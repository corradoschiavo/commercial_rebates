# Copyright (c) 2026, Corrado Schiavo and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {
            "label": _("Contratto"),
            "fieldname": "contract",
            "fieldtype": "Link",
            "options": "Rebate Contract",
            "width": 160
        },
        {
            "label": _("Titolo Contratto"),
            "fieldname": "contract_title",
            "fieldtype": "Data",
            "width": 180
        },
        {
            "label": _("Cliente"),
            "fieldname": "customer",
            "fieldtype": "Link",
            "options": "Customer",
            "width": 180
        },
        {
            "label": _("Riga"),
            "fieldname": "line_num",
            "fieldtype": "Int",
            "width": 60
        },
        {
            "label": _("Nota di Credito"),
            "fieldname": "sales_invoice",
            "fieldtype": "Link",
            "options": "Sales Invoice",
            "width": 160
        },
        {
            "label": _("Data Emissione"),
            "fieldname": "posting_date",
            "fieldtype": "Date",
            "width": 110
        },
        {
            "label": _("Importo (€)"),
            "fieldname": "amount",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": _("Codice IVA"),
            "fieldname": "tax_template",
            "fieldtype": "Link",
            "options": "Sales Taxes and Charges Template",
            "width": 130
        },
        {
            "label": _("Stato ERPNext"),
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 150
        },
        {
            "label": _("Causale / Note"),
            "fieldname": "remarks",
            "fieldtype": "Data",
            "width": 240
        }
    ]


def get_data(filters):
    conditions = []
    values = {}

    if filters.get("company"):
        conditions.append("rc.company = %(company)s")
        values["company"] = filters["company"]

    if filters.get("contract"):
        conditions.append("rld.parent = %(contract)s")
        values["contract"] = filters["contract"]

    if filters.get("customer"):
        conditions.append("(rld.customer = %(customer)s OR rc.customer = %(customer)s)")
        values["customer"] = filters["customer"]

    if filters.get("from_date"):
        conditions.append("rld.posting_date >= %(from_date)s")
        values["from_date"] = filters["from_date"]

    if filters.get("to_date"):
        conditions.append("rld.posting_date <= %(to_date)s")
        values["to_date"] = filters["to_date"]

    where_clause = " AND " + " AND ".join(conditions) if conditions else ""

    query = f"""
        SELECT 
            rld.parent AS contract,
            rc.title AS contract_title,
            IFNULL(rld.customer, rc.customer) AS customer,
            rld.line_num,
            rld.sales_invoice,
            rld.posting_date,
            rld.amount,
            rld.tax_template,
            rld.status,
            rld.remarks,
            si.docstatus AS inv_docstatus,
            si.status AS inv_status,
            si.outstanding_amount AS inv_outstanding
        FROM `tabRebate Line Document` rld
        INNER JOIN `tabRebate Contract` rc ON rc.name = rld.parent
        LEFT JOIN `tabSales Invoice` si ON si.name = rld.sales_invoice
        WHERE 1=1 {where_clause}
        ORDER BY rld.posting_date DESC, rld.creation DESC
    """

    raw_data = frappe.db.sql(query, values, as_dict=True)
    data = []

    for row in raw_data:
        status = row.status or "Bozza (Draft)"
        if row.inv_docstatus == 2:
            status = "Annullata (Cancelled)"
        elif row.inv_docstatus == 1:
            if flt(row.inv_outstanding) == 0.0 or row.inv_status in ["Paid", "Credit Note Issued"]:
                status = "Pagata / Compensata (Paid)"
            else:
                status = "Sottomessa / Emessa (Submitted)"
        elif row.inv_docstatus == 0:
            status = "Bozza (Draft)"

        if filters.get("status"):
            filter_st = filters["status"].lower()
            if filter_st not in status.lower():
                continue

        row.status = status
        data.append(row)

    return data
