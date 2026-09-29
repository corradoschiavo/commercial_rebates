// Copyright (c) 2026, Corrado Schiavo and contributors
// For license information, please see license.txt

frappe.ui.form.on('Rebate Contract', {
    refresh: function(frm) {
        // Render dell'Estratto Conto e cruscotto
        renderRebateDashboardIndicators(frm);
        renderEstrattoConto(frm);

        if (frm.is_new()) return;

        // 1. Bottone Principale: Calcola Premi e Conguaglio (in primo piano, blu)
        frm.add_custom_button(__('Calcola Premi & Conguaglio'), function() {
            frappe.call({
                method: 'commercial_rebates.commercial_rebates.doctype.rebate_contract.rebate_contract.calculate_rebates',
                args: { contract_name: frm.doc.name },
                freeze: true,
                freeze_message: __('Calcolo vendite e conguaglio in corso...'),
                callback: function(r) {
                    if (r.message && r.message.status === 'success') {
                        frappe.show_alert({
                            message: __('Calcolo completato: Residuo da Liquidare € {0}', [format_currency(r.message.total_settlement)]),
                            indicator: 'green'
                        }, 5);
                        frm.reload_doc();
                    }
                }
            });
        }).addClass('btn-primary');

        // 2. Bottone: Genera Nota di Credito (in primo piano)
        if (frm.doc.lines && frm.doc.lines.length > 0) {
            frm.add_custom_button(__('Genera Nota di Credito'), function() {
                openCreditNoteDialog(frm);
            }).addClass('btn-info');
        }

        // 3. Bottone: Inquiry / Estratto Conto Globale Report
        frm.add_custom_button(__('Inquiry Documenti Emessi'), function() {
            frappe.set_route('query-report', 'Estratto Conto Premi e Note di Credito', {
                contract: frm.doc.name
            });
        });
    }
});

function renderRebateDashboardIndicators(frm) {
    if (!frm.doc.name || frm.is_new()) return;

    if (frm.doc.total_settlement > 0) {
        frm.dashboard.set_headline_alert(
            __('Residuo da Liquidare (Conguaglio): <b>€ {0}</b> &nbsp;|&nbsp; Maturato: <b>€ {1}</b> &nbsp;|&nbsp; Già Liquidato: <b>€ {2}</b>', [
                format_currency(frm.doc.total_settlement),
                format_currency(frm.doc.total_award),
                format_currency(frm.doc.total_liquidated)
            ]),
            'blue'
        );
    } else if (frm.doc.total_award > 0 && frm.doc.total_settlement === 0) {
        frm.dashboard.set_headline_alert(
            __('✓ Tutti i premi maturati risultano interamente liquidati (Totale: € {0})', [format_currency(frm.doc.total_award)]),
            'green'
        );
    }
}

function renderEstrattoConto(frm) {
    if (!frm.fields_dict.estratto_conto_html) return;

    let docs = frm.doc.documents || [];
    let total_award = flt(frm.doc.total_award);
    let total_liquidated = flt(frm.doc.total_liquidated);
    let total_settlement = flt(frm.doc.total_settlement);

    let summaryCardHtml = `
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px;">
            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 16px;">
                <div style="font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: 600;">Totale Premio Maturato</div>
                <div style="font-size: 18px; font-weight: 700; color: #1e293b; margin-top: 4px;">€ ${format_currency(total_award)}</div>
            </div>
            <div style="background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 12px 16px;">
                <div style="font-size: 11px; text-transform: uppercase; color: #1d4ed8; font-weight: 600;">Note di Credito Emesse</div>
                <div style="font-size: 18px; font-weight: 700; color: #1e40af; margin-top: 4px;">€ ${format_currency(total_liquidated)}</div>
            </div>
            <div style="background: #ecfdf5; border: 1px solid #a7f3d0; border-radius: 8px; padding: 12px 16px;">
                <div style="font-size: 11px; text-transform: uppercase; color: #047857; font-weight: 600;">Residuo da Liquidare (Conguaglio)</div>
                <div style="font-size: 18px; font-weight: 700; color: #065f46; margin-top: 4px;">€ ${format_currency(total_settlement)}</div>
            </div>
        </div>
    `;

    if (docs.length === 0) {
        let emptyHtml = `
            ${summaryCardHtml}
            <div style="padding: 24px; text-align: center; background: #fafafa; border: 1px dashed #cbd5e1; border-radius: 8px;">
                <div style="font-size: 14px; font-weight: 600; color: #475569;">Nessuna Nota di Credito o documento emesso per questo contratto.</div>
                <div style="font-size: 12px; color: #94a3b8; margin-top: 6px;">
                    Utilizza il pulsante <b>"Genera Nota di Credito"</b> in alto per emettere una nota di credito di conguaglio per le condizioni maturate.
                </div>
            </div>
        `;
        frm.fields_dict.estratto_conto_html.$wrapper.html(emptyHtml);
        return;
    }

    let rowsHtml = '';
    docs.forEach(function(d) {
        let status = d.status || 'Bozza (Draft)';
        let badgeStyle = 'background: #fef3c7; color: #92400e; border: 1px solid #fcd34d;'; // Bozza
        if (status.includes('Sottomessa') || status.includes('Submitted')) {
            badgeStyle = 'background: #dbeafe; color: #1e40af; border: 1px solid #93c5fd;'; // Sottomessa
        } else if (status.includes('Pagata') || status.includes('Paid')) {
            badgeStyle = 'background: #d1fae5; color: #065f46; border: 1px solid #6ee7b7;'; // Pagata
        } else if (status.includes('Annullata') || status.includes('Cancelled')) {
            badgeStyle = 'background: #fee2e2; color: #991b1b; border: 1px solid #fca5a5;'; // Annullata
        }

        let formattedDate = d.posting_date ? frappe.datetime.str_to_user(d.posting_date) : '-';

        rowsHtml += `
            <tr style="border-bottom: 1px solid #e2e8f0; font-size: 12px;">
                <td style="padding: 10px 12px; font-weight: 600; color: #475569;">#${d.line_num || 1}</td>
                <td style="padding: 10px 12px;">
                    <a href="javascript:void(0)" onclick="frappe.set_route('Form', 'Sales Invoice', '${d.sales_invoice}')" style="font-weight: 600; color: #2563eb; text-decoration: underline;">
                        ${d.sales_invoice}
                    </a>
                </td>
                <td style="padding: 10px 12px; color: #64748b;">${formattedDate}</td>
                <td style="padding: 10px 12px; color: #334155;">${d.customer || frm.doc.customer || '-'}</td>
                <td style="padding: 10px 12px; color: #475569;">${d.remarks || '-'}</td>
                <td style="padding: 10px 12px; text-align: right; font-weight: 700; color: #0f172a;">€ ${format_currency(d.amount)}</td>
                <td style="padding: 10px 12px; text-align: center;">
                    <span style="display: inline-block; padding: 2px 8px; border-radius: 9999px; font-size: 11px; font-weight: 600; ${badgeStyle}">
                        ${status}
                    </span>
                </td>
                <td style="padding: 10px 12px; text-align: center;">
                    <button class="btn btn-default btn-xs" onclick="frappe.set_route('Form', 'Sales Invoice', '${d.sales_invoice}')">
                        Apri Documento
                    </button>
                </td>
            </tr>
        `;
    });

    let tableHtml = `
        ${summaryCardHtml}
        <div style="border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; background: #fff; margin-bottom: 15px;">
            <div style="padding: 10px 14px; background: #f8fafc; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center;">
                <span style="font-weight: 600; color: #334155; font-size: 13px;">Estratto Conto Note di Credito Collegate (${docs.length} documenti)</span>
                <button class="btn btn-default btn-xs" id="btn-sync-statement" onclick="cur_frm.reload_doc();">
                    ↻ Aggiorna Stati da ERPNext
                </button>
            </div>
            <table class="table" style="width: 100%; margin: 0; border-collapse: collapse;">
                <thead style="background: #f1f5f9; color: #475569; font-size: 11px; text-transform: uppercase;">
                    <tr>
                        <th style="padding: 8px 12px;">Rif. Riga</th>
                        <th style="padding: 8px 12px;">Nota di Credito</th>
                        <th style="padding: 8px 12px;">Data</th>
                        <th style="padding: 8px 12px;">Cliente</th>
                        <th style="padding: 8px 12px;">Causale</th>
                        <th style="padding: 8px 12px; text-align: right;">Importo Liquidato</th>
                        <th style="padding: 8px 12px; text-align: center;">Stato ERPNext</th>
                        <th style="padding: 8px 12px; text-align: center;">Azioni</th>
                    </tr>
                </thead>
                <tbody>
                    ${rowsHtml}
                </tbody>
            </table>
        </div>
    `;

    frm.fields_dict.estratto_conto_html.$wrapper.html(tableHtml);
}

function openCreditNoteDialog(frm) {
    let line_options = frm.doc.lines.map(l => {
        let label = `Riga #${l.line_num}: ${l.description} (Da Liquidare: € ${format_currency(l.settlement_amount)})`;
        return { label: label, value: l.line_num };
    });

    let first_line = frm.doc.lines[0];

    let d = new frappe.ui.Dialog({
        title: __('Genera Nota di Credito (Conguaglio Premio)'),
        fields: [
            {
                fieldname: 'line_num',
                fieldtype: 'Select',
                label: __('Seleziona Riga Contratto'),
                options: line_options,
                default: first_line.line_num,
                reqd: 1,
                onchange: function() {
                    let sel_line_num = d.get_value('line_num');
                    let sel_line = frm.doc.lines.find(l => l.line_num == sel_line_num);
                    if (sel_line) {
                        d.set_value('amount', sel_line.settlement_amount);
                        d.set_value('remarks', `Liquidazione Premio Fuori Fattura: ${frm.doc.name} - Riga #${sel_line.line_num} (${sel_line.description})`);
                        updateDialogHelpText(d, sel_line);
                    }
                }
            },
            {
                fieldname: 'customer',
                fieldtype: 'Link',
                label: __('Cliente Intestatario'),
                options: 'Customer',
                default: frm.doc.customer || '',
                reqd: 1
            },
            {
                fieldname: 'conguaglio_info',
                fieldtype: 'HTML'
            },
            {
                fieldname: 'amount',
                fieldtype: 'Currency',
                label: __('Importo da Emettere (€) - Modificabile a Discrezione'),
                default: first_line.settlement_amount,
                reqd: 1
            },
            {
                fieldname: 'tax_template',
                fieldtype: 'Link',
                label: __('Aliquota / Codice IVA'),
                options: 'Sales Taxes and Charges Template',
                default: first_line.tax_template || ''
            },
            {
                fieldname: 'remarks',
                fieldtype: 'Small Text',
                label: __('Causale / Oggetto Nota di Credito'),
                default: `Liquidazione Premio Fuori Fattura: ${frm.doc.name} - Riga #${first_line.line_num} (${first_line.description})`
            }
        ],
        primary_action_label: __('Emetti Nota di Credito (Bozza)'),
        primary_action: function(values) {
            frappe.call({
                method: 'commercial_rebates.commercial_rebates.doctype.rebate_contract.rebate_contract.emit_rebate_credit_note',
                args: {
                    contract_name: frm.doc.name,
                    line_num: values.line_num,
                    customer: values.customer,
                    amount: values.amount,
                    tax_template: values.tax_template,
                    remarks: values.remarks
                },
                freeze: true,
                freeze_message: __('Creazione Nota di Credito in ERPNext...'),
                callback: function(r) {
                    if (r.message && r.message.status === 'success') {
                        d.hide();
                        frappe.msgprint({
                            title: __('Nota di Credito Creata'),
                            indicator: 'green',
                            message: __('È stata creata la Nota di Credito <b>{0}</b> in stato Bozza.<br><br><button class="btn btn-xs btn-primary" onclick="frappe.set_route(\'Form\', \'Sales Invoice\', \'{0}\')">Apri Documento in ERPNext</button>', [r.message.invoice_name])
                        });
                        frm.reload_doc();
                    }
                }
            });
        }
    });

    updateDialogHelpText(d, first_line);
    d.show();
}

function updateDialogHelpText(dialog, line) {
    let html = `
        <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px; margin: 10px 0; font-size: 12px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                <span>Premio Maturato: <b>€ ${format_currency(line.award_amount)}</b></span>
                <span>Già Liquidato: <b>€ ${format_currency(line.already_liquidated)}</b></span>
                <span style="color: #059669;">Conguaglio Proposto: <b>€ ${format_currency(line.settlement_amount)}</b></span>
            </div>
            <div style="color: #64748b; font-size: 11px;">
                <i>Il sistema propone il conguaglio spettante, ma hai la piena discrezionalità di modificare la cifra nel campo sottostante.</i>
            </div>
        </div>
    `;
    dialog.fields_dict.conguaglio_info.$wrapper.html(html);
}
