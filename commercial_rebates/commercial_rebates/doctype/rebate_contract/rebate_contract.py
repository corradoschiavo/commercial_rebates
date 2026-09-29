# Copyright (c) 2026, Corrado Schiavo and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, nowdate


class RebateContract(Document):
    def validate(self):
        """Ricalcola i totali di testata del contratto e sincronizza gli stati dei documenti."""
        sync_document_statuses(self)

        total_award = 0.0
        total_liquidated = 0.0
        total_settlement = 0.0

        for line in self.lines:
            total_award += flt(line.award_amount)
            total_liquidated += flt(line.already_liquidated)
            total_settlement += flt(line.settlement_amount)

        self.total_award = round(total_award, 2)
        self.total_liquidated = round(total_liquidated, 2)
        self.total_settlement = round(total_settlement, 2)


def sync_document_statuses(doc):
    """
    Sincronizza in tempo reale lo stato di ciascuna Nota di Credito / Sales Invoice
    collegata al contratto verificando docstatus e outstanding_amount sul database ERPNext.
    """
    has_changes = False
    for row in (doc.documents or []):
        if not row.sales_invoice:
            continue

        inv = frappe.db.get_value(
            "Sales Invoice",
            row.sales_invoice,
            ["docstatus", "status", "posting_date", "grand_total", "outstanding_amount", "customer"],
            as_dict=True
        )
        if not inv:
            continue

        real_status = "Bozza (Draft)"
        if inv.docstatus == 2:
            real_status = "Annullata (Cancelled)"
        elif inv.docstatus == 1:
            if flt(inv.outstanding_amount) == 0.0 or inv.status in ["Paid", "Credit Note Issued"]:
                real_status = "Pagata / Compensata (Paid)"
            else:
                real_status = "Sottomessa / Emessa (Submitted)"
        elif inv.docstatus == 0:
            real_status = "Bozza (Draft)"

        if row.status != real_status:
            row.status = real_status
            has_changes = True

        if inv.posting_date and str(row.posting_date) != str(inv.posting_date):
            row.posting_date = inv.posting_date
            has_changes = True

        if inv.customer and not row.customer:
            row.customer = inv.customer
            has_changes = True

    return has_changes


@frappe.whitelist()
def calculate_rebates(contract_name):
    """
    Motore analitico nativo per la valutazione del contratto premi e del conguaglio spettante.
    Interroga direttamente il database di ERPNext sulle Sales Invoice sottomesse (docstatus = 1).
    """
    doc = frappe.get_doc("Rebate Contract", contract_name)
    sync_document_statuses(doc)

    is_contract_active = (doc.status == "Attivo")
    default_from = doc.valid_from or "1900-01-01"
    default_to = doc.valid_to or "2099-12-31"

    # Determina l'elenco dei clienti da monitorare
    target_customers = []
    if doc.target_type == "Customer" and doc.customer:
        target_customers = [doc.customer]
    elif doc.target_type == "Customer Group" and doc.customer_group:
        target_customers = frappe.db.get_list(
            "Customer",
            filters={"customer_group": doc.customer_group},
            pluck="name"
        )

    for line in doc.lines:
        is_line_active = (line.status == "Attivo")
        v_from = line.valid_from or default_from
        v_to = line.valid_to or default_to

        accumulated_turnover = 0.0
        accumulated_qty = 0.0

        if is_contract_active and is_line_active and target_customers:
            # Query delle fatture di vendita conformi
            invoices = frappe.db.sql("""
                SELECT 
                    si.name,
                    si.posting_date,
                    sii.item_code,
                    sii.item_group,
                    sii.net_amount,
                    sii.qty
                FROM `tabSales Invoice` si
                INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
                WHERE si.docstatus = 1
                  AND si.is_return = 0
                  AND si.company = %s
                  AND si.customer IN %s
                  AND si.posting_date BETWEEN %s AND %s
            """, (doc.company, tuple(target_customers), v_from, v_to), as_dict=True)

            for inv in invoices:
                # Filtro Gruppo Articolo
                if line.item_group and line.item_group.lower() not in ["all", "tutti", "all item groups"]:
                    if inv.item_group != line.item_group:
                        continue
                # Filtro Articolo Specifico
                if line.item_code and line.item_code.lower() not in ["all", "tutti"]:
                    if inv.item_code != line.item_code:
                        continue

                accumulated_turnover += flt(inv.net_amount)
                accumulated_qty += flt(inv.qty)

        metric_value = accumulated_turnover if line.basis == "turnover" else accumulated_qty
        threshold = flt(line.threshold)
        is_reached = (metric_value >= threshold) if (is_contract_active and is_line_active) else False

        award_amount = 0.0
        if is_reached:
            if line.calc_type == "percentage":
                award_amount = round(accumulated_turnover * (flt(line.calc_value) / 100.0), 2)
            else:
                award_amount = round(flt(line.calc_value), 2)

        # Calcolo quote già liquidate (somma note di credito emesse non annullate + manuale)
        docs_liquidated = 0.0
        for d in (doc.documents or []):
            if d.line_num == line.line_num:
                status_low = (d.status or "").lower()
                if "annullat" not in status_low and "cancel" not in status_low:
                    docs_liquidated += flt(d.amount)

        manual_liquidated = flt(line.manual_liquidated_amount)
        already_liquidated = round(docs_liquidated + manual_liquidated, 2)
        settlement_amount = max(0.0, round(award_amount - already_liquidated, 2)) if is_reached else 0.0

        # Aggiornamento riga
        line.current_sales = round(accumulated_turnover, 2)
        line.is_reached = 1 if is_reached else 0
        line.award_amount = award_amount
        line.already_liquidated = already_liquidated
        line.settlement_amount = settlement_amount

    doc.save()
    return {
        "status": "success",
        "message": _("Ricalcolo completato con successo"),
        "total_award": doc.total_award,
        "total_liquidated": doc.total_liquidated,
        "total_settlement": doc.total_settlement
    }


@frappe.whitelist()
def emit_rebate_credit_note(contract_name, line_num, customer, amount, tax_template=None, remarks=None):
    """
    Genera una Nota di Credito nativa in ERPNext (Sales Invoice TD04 con is_return = 1)
    in stato Bozza (Draft), comprensiva della tabella imposte conforme alla fatturazione elettronica.
    """
    doc = frappe.get_doc("Rebate Contract", contract_name)
    line_num = int(line_num)
    amount = flt(amount)

    target_line = None
    for l in doc.lines:
        if l.line_num == line_num:
            target_line = l
            break

    if not target_line:
        frappe.throw(_("Riga contratto #{0} non trovata.").format(line_num))

    if amount <= 0:
        frappe.throw(_("L'importo della Nota di Credito deve essere maggiore di zero."))

    used_tax = tax_template or target_line.tax_template or ""
    line_desc = target_line.description or _("Premio Fuori Fattura")
    doc_remarks = remarks or _("Liquidazione Premio Fuori Fattura: {0} - Riga #{1} ({2})").format(
        doc.name, line_num, line_desc
    )

    company_doc = frappe.get_doc("Company", doc.company)

    # 1. Creazione documento Sales Invoice di reso / nota credito (TD04)
    sinv = frappe.new_doc("Sales Invoice")
    sinv.is_return = 1
    sinv.customer = customer or doc.customer
    sinv.company = doc.company
    sinv.posting_date = nowdate()
    sinv.remarks = doc_remarks
    if company_doc.cost_center:
        sinv.cost_center = company_doc.cost_center

    # Riga articolo nota credito
    item_dict = {
        "item_name": _("Liquidazione Premio Fuori Fattura"),
        "description": f"{line_desc} (Rif. Contratto: {doc.name})",
        "qty": -1,
        "rate": amount,
        "amount": -amount
    }
    if company_doc.default_income_account:
        item_dict["income_account"] = company_doc.default_income_account
    if company_doc.cost_center:
        item_dict["cost_center"] = company_doc.cost_center
    if target_line.item_code and frappe.db.exists("Item", target_line.item_code):
        item_dict["item_code"] = target_line.item_code

    sinv.append("items", item_dict)

    # 2. Configurazione Imposte (obbligatoria per E-Invoicing / Fattura Elettronica)
    if not used_tax:
        used_tax = company_doc.default_sales_tax_template or \
                   frappe.db.get_value("Sales Taxes and Charges Template", {"company": doc.company, "is_default": 1}, "name") or \
                   frappe.db.get_value("Sales Taxes and Charges Template", {"company": doc.company}, "name")

    if used_tax and frappe.db.exists("Sales Taxes and Charges Template", used_tax):
        sinv.taxes_and_charges = used_tax
        tax_template_doc = frappe.get_doc("Sales Taxes and Charges Template", used_tax)
        sinv.set("taxes", [])
        for t in tax_template_doc.taxes:
            sinv.append("taxes", {
                "charge_type": t.charge_type,
                "account_head": t.account_head,
                "rate": t.rate,
                "description": t.description,
                "included_in_print_rate": getattr(t, "included_in_print_rate", 0),
                "cost_center": getattr(t, "cost_center", None) or company_doc.cost_center
            })
    else:
        # Fallback: crea riga imposta generica se non è configurato alcun template
        tax_account = frappe.db.get_value("Account", {"company": doc.company, "account_type": "Tax", "is_group": 0}, "name")
        if tax_account:
            sinv.append("taxes", {
                "charge_type": "On Net Total",
                "account_head": tax_account,
                "rate": 22.0,
                "description": "IVA 22%",
                "cost_center": company_doc.cost_center
            })

    # Calcola totali ed imposte di ERPNext
    try:
        sinv.run_method("calculate_taxes_and_totals")
    except Exception:
        pass

    # Inserimento in stato Bozza (Draft)
    sinv.flags.ignore_permissions = True
    sinv.insert()

    # 3. Registrazione nello storico del contratto
    doc.append("documents", {
        "line_num": line_num,
        "sales_invoice": sinv.name,
        "posting_date": sinv.posting_date,
        "customer": sinv.customer,
        "amount": amount,
        "tax_template": used_tax,
        "status": _("Bozza (Draft)"),
        "remarks": doc_remarks
    })

    target_line.credit_note_ref = sinv.name
    target_line.already_liquidated = flt(target_line.already_liquidated) + amount
    target_line.settlement_amount = max(0.0, flt(target_line.award_amount) - target_line.already_liquidated)

    doc.save()

    return {
        "status": "success",
        "invoice_name": sinv.name,
        "message": _("Nota di Credito {0} generata con successo in stato Bozza.").format(sinv.name)
    }


@frappe.whitelist()
def get_contract_statement(contract_name):
    """
    Ritorna l'estratto conto completo e sincronizzato delle Note di Credito emesse per il contratto.
    """
    doc = frappe.get_doc("Rebate Contract", contract_name)
    if sync_document_statuses(doc):
        doc.save()

    docs_data = []
    for d in (doc.documents or []):
        docs_data.append({
            "line_num": d.line_num,
            "sales_invoice": d.sales_invoice,
            "posting_date": str(d.posting_date) if d.posting_date else "",
            "customer": d.customer,
            "amount": flt(d.amount),
            "tax_template": d.tax_template or "",
            "status": d.status or "Bozza (Draft)",
            "remarks": d.remarks or ""
        })

    return {
        "contract": doc.name,
        "title": doc.title,
        "customer": doc.customer,
        "total_award": doc.total_award,
        "total_liquidated": doc.total_liquidated,
        "total_settlement": doc.total_settlement,
        "documents": docs_data
    }
