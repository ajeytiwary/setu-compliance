# Setu EU Market Access OS — Client Demo Guide (Real-Data Walkthrough)

**Audience:** EU importer / Indian steel exporter pilot stakeholder (commercial + compliance).
**Duration:** 45–60 min. **Server:** `http://localhost:8765` (UI at `/`).
**Repo:** `ajeytiwary/setu-compliance`, branch `main`.

> **Honesty header (read this first on the call).** Commercial entities, invoice
> values, shipment identifiers (`HRC-NL-001` …) and order-book figures are
> **synthetic demo data**. Regulatory reference tables below are **official EU
> publications**, snapshotted with SHA-256 provenance. The demo proves the
> *wiring* (ERP → CBAM math → steel safeguard → FTA preview → DPP →
> risk drilldown); a paid pilot replaces synthetic commercial rows with the
> client's SAP/MES/EMS extracts.

---

## 1. Data provenance — what is real, what is synthetic

| # | Dataset | Authority | Status in this demo | Provenance |
|---|---------|-----------|---------------------|------------|
| 1 | CBAM default values (corrected 2025/2621 + 2026/1740) | EU TAXUD (OFFICIAL, not legal authority) | ✅ LOADED — 11,469 rows, `data/cbam/defaults.csv` + `data/cbam/defaults.json` | Snapshot `data/sources/cbam_defaults/latest.json`, 13,367 raw records, sha `90058381…` |
| 2 | CBAM benchmarks (2025/2620) | EU TAXUD (OFFICIAL) | ✅ LOADED — 570 rows, `data/cbam/benchmarks.csv` + `data/cbam/benchmarks.json` | Snapshot `data/sources/cbam_benchmarks/latest.json`, 1,815 raw records, sha `b79108b0…` |
| 3 | EU steel safeguard categories + CN mapping (2026/1384 + 2026/1457) | EUR-Lex (LEGAL) | ✅ CHECKED-IN — `data/eu_steel_measure_2026.json` (live EUR-Lex fetch returns empty via urllib; ELI URLs recorded in API response) | `legal_basis` in every `/regulatory/steel/evaluate` response |
| 4 | EU–India FTA status | EU Trade policy page (OFFICIAL) | ✅ CHECKED-IN — `EU_IN_FTA_2026_NEGOTIATED`, `NEGOTIATED_NOT_IN_FORCE`, concluded 2026-01-27 | Every FTA response carries `guardrail` + source URL |
| 5 | ERP/MES/EMS/LIMS/GST/DGFT/ICEGATE/verifier/logistics samples | Synthetic (14 CSVs in `connectors/samples/`) | ✅ IMPORTED — 14/14 connectors SUCCESS | `GET /api/integrations/canonical/summary` |
| 6 | 12-shipment client portfolio (`HRC-NL-001` … `HRC-IT-012`) | Synthetic commercial | ✅ LOADED via `POST /api/shipments` | `examples/client_portfolio_12_shipments.json` |
| 7 | TARIC measures, quota balances, EUCDM, ECHA, SCIP, sanctions, COMEXT, telemetry | EU TAXUD/ECHA/Eurostat (OFFICIAL) | ✅ VERSIONED PIPELINE — auto resolvers (`python scripts/sync_sources.py --strict`, 5 sources via link-discovery) + weekly/manual materialization (`--dataset/--all/--file/--url/--force`, raw→normalized→manifest with SHA-256; bot-blocked publishers via browser `--file`) | `GET /api/data-sources` (manifest pointers) + `POST /api/data-sources/{ds}/sync` manual refresh; see `docs/SOURCE_SYNC.md` |
| 8 | Public JSW Vijayanagar case (`PUBLIC-JSW-VJ-HRC-EU-2026`) | Company annual report + EPD `EPD-IES-0005172:001` + Commission template | ✅ SEEDED on first boot | `app/seed.py` |

**Key message for the client:** CBAM math runs on the *actual* Commission
tables (country-named sheets, route indicators `(A)/(C)`, 10 % markup for 2026).
Quota *balances* are never invented — the steel endpoint returns
`QUOTA_BALANCE_REQUIRED` until a live QUOTA-database balance is supplied.

---

## 2. One-time setup (run before the meeting)

```bash
cd /home/plasmion/git/setu-market-access-mvp-production
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python -r requirements.txt
uv pip install --python .venv/bin/python openpyxl   # official XLSX parsing

# 2a. Download official CBAM workbooks (TAXUD URLs in config/data_sources.json)
PYTHONPATH=. .venv/bin/python scripts/sync_official_reference_data.py
# → data/official/cbam-defaults-official.json + cbam-benchmarks-official.json
#   (steel annex fetch currently yields 0 categories — checked-in JSON is used)

# 2b. Convert to importable CSVs (handles per-country sheets + N/A cells)
PYTHONPATH=. .venv/bin/python scripts/convert_official_to_imports.py
# → data/cbam/defaults.csv (11,469 rows) + data/cbam/benchmarks.csv (570 rows)

# 2c. Load reference tables into the app (in-process; the HTTP import caps
#     request size, so the 440 KB defaults file is loaded directly)
PYTHONPATH=. .venv/bin/python -c "
from app.cbam_definitive_v2 import import_defaults, import_benchmarks
print(len(import_defaults(open('data/cbam/defaults.csv').read())['records']))
print(len(import_benchmarks(open('data/cbam/benchmarks.csv').read())['records']))"

# 2d. Record SHA-256 snapshots (provenance for the audit slide)
PYTHONPATH=. .venv/bin/python -c "
from app.data_sources import snapshot
print(snapshot('cbam_defaults')['record_count'], snapshot('cbam_defaults')['sha256'][:12])
print(snapshot('cbam_benchmarks')['record_count'], snapshot('cbam_benchmarks')['sha256'][:12])"

# 2e. Load ERP/MES/EMS evidence backbone (14/14 should succeed)
PYTHONPATH=. .venv/bin/python -c "
from app.integrations import import_sample, integration_catalog
for c in integration_catalog()['connectors']: import_sample(c['code'])
print('14/14 imported')"

# 2f. Start the server (leave running)
PYTHONPATH=. nohup .venv/bin/python -m uvicorn app.main:app --port 8765 >/tmp/setu_server.log 2>&1 &
curl -s localhost:8765/api/dashboard | head -c 120

# 2g. Load the 12-shipment demo portfolio
PYTHONPATH=. .venv/bin/python -c "
import json, urllib.request
base='http://localhost:8765'
def post(p,b):
    r=urllib.request.Request(base+p,data=json.dumps(b).encode(),headers={'Content-Type':'application/json'})
    return json.loads(urllib.request.urlopen(r,timeout=30).read().decode())
for s in json.load(open('examples/client_portfolio_12_shipments.json'))['shipments']:
    post('/api/shipments',{'shipment_no':s['shipment_ref'],'facility':'JSW Vijayanagar',
        'importer':'Demo EU importer '+s['destination_country'],
        'destination_country':s['destination_country'],'cn_code':s['cn_code'],
        'tonnes':s['quantity_t'],'value_eur':s.get('customs_value_eur') or 100000})
print('12 shipments created')"

# 2h. Sanity: 44/44 tests green
.venv/bin/python -m pytest -q
```

---

## 3. Live demo script (12 steps, ~45 min)

> All `shipment_id` path params accept **either the UUID or the human
> `shipment_no`** (e.g. `HRC-NL-001`). This was the "shipment number one"
> fix — demo it explicitly in Step 3.

### Step 0 — Landing (2 min)
Open `http://localhost:8765/`. Show the dashboard cards.
```bash
curl -s localhost:8765/api/dashboard | python3 -m json.tool | head -30
```
**Say:** "28 shipments, €6.6 M bound. One tile is real regulation, the rest is
your money at risk until evidence lands."

### Step 1 — Order book: where is my revenue? (4 min)
```bash
curl -s localhost:8765/api/market-access/order-book | python3 -m json.tool | head -40
```
**Say:** "€7.8 M order book, 45 % market-ready. CBAM exposure €208 k.
The `SYNTHETIC_OPERATIONAL_DEMO` warning is deliberate — we never dress
demo euros as audited euros."

### Step 2 — Risk drilldown: which country, which rule? (5 min)
```bash
curl -s localhost:8765/api/market-access/risk-drilldown | python3 -m json.tool | head -60
```
**Say:** "`data_status: CONNECTED_SHIPMENT_DATA`. NL €1.17 M at risk across
named shipments with blocker counts. Click into `HRC-NL-001` — 4 blockers."

### Step 3 — Shipment by human number (3 min) ⭐ *the re-implemented feature*
```bash
curl -s localhost:8765/api/shipments/HRC-NL-001 | python3 -m json.tool | head -40
```
**Say:** "Ops teams quote `HRC-NL-001`, not UUIDs. Every route —
`GET shipment`, `POST evidence`, `GET dpp`, `POST simulate-remediation` —
resolves both. Try the UUID too; same record."

### Step 4 — Evidence: close one blocker live (5 min)
```bash
curl -s -X POST localhost:8765/api/shipments/HRC-NL-001/evidence \
  -H 'Content-Type: application/json' \
  -d '{"requirement_code":"CBAM_EMISSIONS","filename":"ems_report.pdf","evidence_type":"EMS_REPORT","issuer":"Plant EMS"}'
curl -s localhost:8765/api/shipments/HRC-NL-001 | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['score']['blockers'])"
```
**Say:** "SHA-256 hashed, counted against the requirement, audit-logged.
Watch the blocker list shrink. `CBAM_VERIFICATION` / `SUPPLIER_DATA` /
`CBAM_EMISSIONS` stay human-gated — evidence alone never auto-passes them."

### Step 5 — CBAM default math on official tables (6 min, the money slide)
Full happy path (pig-iron CN with both a default *and* a benchmark):
```bash
curl -s -X POST localhost:8765/api/cbam/v2/calculate -H 'Content-Type: application/json' \
  -d '{"payload":{"origin_country":"IN","cn_code":"72011011","value_type":"DEFAULT","reporting_period":2026,"activity_level_t":20,"cscf":0.9}}' \
  | python3 -m json.tool
```
Expected: `status: CALCULATED`, `specific_embedded_emissions: 2.783 tCO₂e/t`
(2.53 + 10 % 2026 markup), benchmark 1.089, free allocation computed.
Then the honest HRC case:
```bash
curl -s -X POST localhost:8765/api/cbam/v2/calculate -H 'Content-Type: application/json' \
  -d '{"payload":{"origin_country":"IN","cn_code":"72083900","value_type":"DEFAULT","reporting_period":2026}}' \
  | python3 -m json.tool
```
Expected: `default.available: true` (4.708 via 4-digit `7208 (C)` fallback),
`status: BLOCKED` on `BENCHMARK_NOT_FOUND` — the official benchmark table
lists `72083900 (C) 0.044` at 8-digit granularity and the matcher is exact
there. **Say:** "The engine would rather block than invent a benchmark.
That conservatism is the product."

### Step 6 — Steel safeguard: quota truth, not quota fiction (4 min)
```bash
curl -s -X POST localhost:8765/api/regulatory/steel/evaluate -H 'Content-Type: application/json' \
  -d '{"payload":{"cn_code":"72083900","origin_country":"IN","import_date":"2026-09-29","quantity_t":20,"customs_value_eur":120000}}' \
  | python3 -m json.tool
```
Expected: `applicable: true`, category `1A`, 50 % out-of-quota duty,
`entitlement_status: QUOTA_BALANCE_REQUIRED`, ELI links to 2026/1384 + 2026/1457.
**Say:** "Category mapping is live. The balance must come from the Commission
QUOTA database at clearance time — we surface the order number, we never
hallucinate the tonnes remaining."

### Step 7 — FTA preview: why 'potential only' (4 min)
```bash
curl -s -X POST localhost:8765/api/fta/origin/evaluate -H 'Content-Type: application/json' \
  -d "{\"payload\": $(cat examples/fta_origin_preview.json)}" | python3 -m json.tool | head -40
curl -s localhost:8765/api/fta/agreements | python3 -m json.tool | head -20
```
Expected: `legal_regime: CURRENT_MFN`, `preference_available: false`,
`proof_of_origin_status: NOT_AVAILABLE_UNDER_FTA_YET`.
**Say:** "Negotiations concluded 2026-01-27, not in force. We show the
technical origin preview *and* the legal guardrail, so nobody books savings
that don't exist yet."

### Step 8 — Supplier network + remediation (4 min)
```bash
curl -s localhost:8765/api/suppliers | python3 -m json.tool | head -30
curl -s localhost:8765/api/remediation | python3 -m json.tool | head -30
curl -s -X POST localhost:8765/api/market-access/shipments/HRC-NL-001/simulate-remediation \
  -H 'Content-Type: application/json' -d '{"requirement_code":"CBAM_EMISSIONS","estimated_cost":5000}' \
  | python3 -m json.tool
```
Expected: `simulation: true, mutated: false`, before/after blocker counts
(4 → 3), revenue-at-risk delta. **Say:** "What-if without touching the
ledger. The CFO sees cost-to-clear per blocker before approving field work."

### Step 9 — Digital Product Passport (3 min)
```bash
curl -s localhost:8765/api/shipments/HRC-NL-001/dpp | python3 -m json.tool | head -30
```
**Say:** "Schema.org JSON-LD, `MVP_READINESS` status, readiness score +
blockers embedded. Steel ESPR fields stay versioned/configurable — we don't
freeze a moving regulation into your passport."

### Step 10 — Integration backbone (3 min)
```bash
curl -s localhost:8765/api/integrations/canonical/summary | python3 -m json.tool | head -30
curl -s localhost:8765/api/live-connections | python3 -m json.tool | head -20
```
**Say:** "14 connectors, canonical types (shipment, genealogy, activity,
trade_document, verification…). Samples today; your SAP SD/MES/EMS endpoints
+ credentials in the pilot. Private connections never touch this demo DB."

### Step 11 — Provenance audit (2 min, close with trust)
```bash
curl -s localhost:8765/api/data-sources | python3 -c \
  "import json,sys; d=json.load(sys.stdin); [print(k,'->',v['snapshot']['record_count'] if v['snapshot'] else None) for k,v in d.items()]"
```
Expected: `cbam_defaults → 13367`, `cbam_benchmarks → 1815`, everything else
`None` with reason. **Say:** "Two green ticks with SHAs, nine honest nulls.
Any vendor showing you twelve green ticks on EU sources without credentials
is parsing landing pages as law."

---

## 4. Objection handling (one-liners)

| Objection | Answer |
|-----------|--------|
| "Is the CBAM number real?" | "The default 2.53 and benchmark 1.089 are Commission-published; the 10 % markup is the 2026 rule. Shipment tonnage is demo." |
| "Why is my HRC shipment BLOCKED?" | "Benchmark granularity — exact-match conservatism. We'd map your mill's route indicator in the pilot rather than loosen the matcher." |
| "Where is the quota balance?" | "Behind the Commission login. We give you the order number + category today, the live balance on day one of integration." |
| "When does the FTA save me money?" | "When it enters into force. Until then we keep you MFN-clean and preview-ready." |
| "Can ops use shipment numbers?" | "Yes — every route accepts UUID or `shipment_no` (Step 3)." |
| "What do you need from us for a pilot?" | "SAP SD + MES genealogy + EMS activity extracts, one verifier contact, one EU importer EORI. 12-week plan in `docs/12_WEEK_PLAN.md`." |

---

## 5. After the call — pilot scoping checklist

- [ ] Confirm 2–3 real CN codes + routes (resolves benchmark granularity question)
- [ ] List SAP/MES/EMS export formats (CSV column mapping vs `connectors/connector-contracts.json`)
- [ ] Name the verifier (maps to `CBAM_VERIFICATION` requirement + verification pack endpoint)
- [ ] EU importer EORI + customs broker (TARIC/quota live lookup credentials)
- [ ] Agree seed scope: 1 real shipment + public JSW case side-by-side
- [ ] Sign data-processing note: pilot DB is client-isolated; demo DB stays synthetic

## 6. Appendix — useful endpoints not in the main script

| Purpose | Method + path |
|---------|---------------|
| UI | `GET /` |
| Dashboard metrics | `GET /api/dashboard` |
| Create shipment | `POST /api/shipments` |
| CBAM actuals calc | `POST /api/cbam/calculate` |
| CBAM verification validate | `POST /api/cbam/verification/validate` |
| CBAM verification pack | `POST /api/cbam/verification/pack` |
| Steel categories import | `POST /api/regulatory/steel/categories/import` |
| Market-access v2 compile | `POST /api/market-access/v2/compile` |
| Customs declaration readiness | `POST /api/customs/declaration-readiness` |
| TARIC resolve | `POST /api/customs/taric/resolve` |
| Public-data status | `GET /api/regulatory/public-data/status` |
| Regulatory registry | `GET /api/regulatory/registry` |
| Steel measure metadata | `GET /api/regulatory/steel-measure` |
| Evidence graph | `GET /api/evidence-graph` |
| Pipeline CBAM (needs SAP SD canonical row) | `POST /api/pipeline/steel/{shipment_ref}/cbam` |
| Pipeline origin | `POST /api/pipeline/steel/{shipment_ref}/origin` |

*Generated from a live verified session: 44/44 pytest green, 28 shipments,
€6.6 M bound, official CBAM tables loaded, snapshots recorded 2026-09-29.*
