# 🏢 Commercial Rebates & Commissions for ERPNext (v15 / v16)

App nativa per **Frappe / ERPNext** sviluppata per la gestione completa di:
- **Contratti Premi Fuori Fattura (Rebates)** con calcolo a soglia (fatturato/quantità, per categoria o articolo), quote liquidate, detrazione acconti manuali e **conguaglio automatico con emissione Note di Credito TD04**.
- **Accordi Provvigionali Agenti** con matrice multi-agente per categoria articolo e gruppo cliente.

Compatibile al 100% con **ERPNext v15 e v16** (locale Docker, self-hosted Linux o Frappe Cloud).

---

## 📦 DocType Inclusi

1. **`Rebate Contract`** (Documento Principale):
   - Intestazione con numerazione `CTR-PREM-.YYYY.-.#####`.
   - Monitoraggio Cliente o Gruppo Cliente, periodo di validità, stato attivo/inattivo.
   - Totali finanziari di testata: *Totale Maturato*, *Totale Già Liquidato*, *Residuo da Liquidare (Conguaglio)*.
2. **`Rebate Contract Line`** (Tabella Figlia):
   - Definizione condizioni di calcolo indipendenti per ciascuna riga.
   - Aliquota IVA specifica di riga (`tax_template`).
   - Campo *Liquidato Manualmente (€)* per acconti o liquidazioni extra.
   - Risultati in tempo reale: *Fatturato Reale*, *Target Raggiunto*, *Premio Maturato*, *Già Liquidato*, *Conguaglio Spettante*.
3. **`Rebate Line Document`** (Tabella Storico Note di Credito):
   - Tracciamento contabile di tutte le Note di Credito (Sales Invoice di reso) collegate alla riga.
4. **`Commission Agreement`** & **`Commission Agreement Line`**:
   - Piani e matrici provvigionali per agente.

---

## ⚡ Azioni Dirette nell'Interfaccia Form di ERPNext

Nella scheda di ciascun contratto in ERPNext sono presenti i pulsanti nativi:
* **`Calcola Premi & Conguaglio`**: interroga direttamente le fatture di vendita sottomesse (`docstatus = 1`) nel database ERPNext e aggiorna immediatamente il conguaglio residuo di ciascuna riga e di testata.
* **`Genera Nota di Credito`**: apre un popup nativo che:
  1. Propone automaticamente il valore di **conguaglio residuo** da corrispondere.
  2. Mantiene la **piena discrezionalità dell'operatore**, permettendo di variare liberamente l'importo.
  3. Crea istantaneamente la **Nota di Credito (Sales Invoice TD04)** in stato Bozza (*Draft*).

---

## 🐳 Installazione su ERPNext Locale (Docker)

Nel terminale del container Docker o del bench ERPNext:
```bash
# 1. Spostarsi nella cartella delle app del bench
cd /home/frappe/frappe-bench/apps

# 2. Copiare o clonare la cartella commercial_rebates qui

# 3. Installare l'app nell'ambiente Python del bench
bench setup requirements
pip install -e /home/frappe/frappe-bench/apps/commercial_rebates

# 4. Installare l'app sul proprio sito ERPNext
bench --site [nome-sito] install-app commercial_rebates
bench --site [nome-sito] migrate
```

---

## ☁️ Installazione su ERPNext v15 Cloud (Frappe Cloud o VPS)

### Opzione A: Frappe Cloud (Consigliata per Cloud)
1. Caricare questa cartella come repository su **GitHub** (es. `https://github.com/tuo-account/commercial_rebates`).
2. Accedere alla dashboard di **Frappe Cloud** (https://frappecloud.com).
3. Andare nella sezione **Apps ➔ Marketplace / Private Apps**.
4. Incollare l'URL del repository GitHub e cliccare su **Add to Site**.
5. Frappe Cloud installerà e migrerà l'app in modo 100% automatizzato.

### Opzione B: VPS Cloud con Bench CLI
```bash
bench get-app https://github.com/tuo-account/commercial_rebates.git
bench --site [nome-sito] install-app commercial_rebates
bench --site [nome-sito] migrate
```
