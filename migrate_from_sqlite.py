"""
Script di migrazione dati: importa i contratti e gli accordi presenti nel database
SQLite 'commercial_contracts.db' direttamente nei nuovi DocType nativi di ERPNext.
"""

import os
import sqlite3
from pathlib import Path

# Percorso database SQLite originario
DB_PATH = Path(__file__).resolve().parent.parent / "erpnext_agent" / "commercial_contracts.db"


def migrate_to_erpnext(client=None):
    if not DB_PATH.exists():
        print(f"[AVVISO] Database SQLite non trovato in {DB_PATH}. Nessun dato da migrare.")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM rebate_contracts")
    contracts = cur.fetchall()
    print(f"Trovati {len(contracts)} contratti da migrare da SQLite.")

    # Se eseguito dentro Frappe Bench:
    try:
        import frappe
        for c in contracts:
            if frappe.db.exists("Rebate Contract", {"title": c["title"]}):
                print(f"Contratto '{c['title']}' già presente, salto.")
                continue

            doc = frappe.new_doc("Rebate Contract")
            doc.title = c["title"]
            doc.status = c["status"]
            doc.target_type = "Customer" if c["target_type"] == "customer" else "Customer Group"
            if doc.target_type == "Customer":
                doc.customer = c["target_name"]
            else:
                doc.customer_group = c["target_name"]
            doc.valid_from = c["valid_from"]
            doc.valid_to = c["valid_to"]
            doc.notes = c["notes"] or ""
            doc.company = "CorradoSchiavo"

            cur.execute("SELECT * FROM rebate_contract_lines WHERE contract_id = ? ORDER BY line_num ASC", (c["id"],))
            lines = cur.fetchall()
            for l in lines:
                doc.append("lines", {
                    "line_num": l["line_num"],
                    "description": l["description"],
                    "status": l["status"],
                    "valid_from": l["valid_from"],
                    "valid_to": l["valid_to"],
                    "item_group": l["item_group"],
                    "basis": l["basis"],
                    "threshold": l["threshold"],
                    "calc_type": l["calc_type"],
                    "calc_value": l["calc_value"],
                    "tax_template": l["tax_template"] or "Italy VAT 22% - CS",
                    "manual_liquidated_amount": l["manual_liquidated_amount"] or 0.0
                })

            doc.insert()
            print(f"✓ Migrato contratto nativo: {doc.name} ({doc.title})")
        
        frappe.db.commit()
        print("Migrazione completata con successo!")

    except ImportError:
        print("[INFO] Lo script è pronto per essere eseguito all'interno del container ERPNext con 'bench execute'.")

    conn.close()


if __name__ == "__main__":
    migrate_to_erpnext()
