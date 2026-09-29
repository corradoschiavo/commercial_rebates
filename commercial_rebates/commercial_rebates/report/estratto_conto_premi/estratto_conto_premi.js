// Copyright (c) 2026, Corrado Schiavo and contributors
// For license information, please see license.txt

frappe.query_reports["Estratto Conto Premi e Note di Credito"] = {
    filters: [
        {
            fieldname: "company",
            label: __("Azienda"),
            fieldtype: "Link",
            options: "Company",
            default: frappe.defaults.get_user_default("Company")
        },
        {
            fieldname: "contract",
            label: __("Contratto Premio"),
            fieldtype: "Link",
            options: "Rebate Contract"
        },
        {
            fieldname: "customer",
            label: __("Cliente"),
            fieldtype: "Link",
            options: "Customer"
        },
        {
            fieldname: "status",
            label: __("Stato Documento"),
            fieldtype: "Select",
            options: "\nBozza\nSottomessa\nPagata\nAnnullata"
        },
        {
            fieldname: "from_date",
            label: __("Da Data Emissione"),
            fieldtype: "Date"
        },
        {
            fieldname: "to_date",
            label: __("A Data Emissione"),
            fieldtype: "Date"
        }
    ],
    formatter: function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        if (column.fieldname === "status" && data) {
            let status = data.status || "";
            if (status.includes("Bozza") || status.includes("Draft")) {
                value = `<span class="indicator-pill yellow">${value}</span>`;
            } else if (status.includes("Sottomessa") || status.includes("Submitted")) {
                value = `<span class="indicator-pill blue">${value}</span>`;
            } else if (status.includes("Pagata") || status.includes("Paid")) {
                value = `<span class="indicator-pill green">${value}</span>`;
            } else if (status.includes("Annullata") || status.includes("Cancelled")) {
                value = `<span class="indicator-pill red">${value}</span>`;
            }
        }
        return value;
    }
};
