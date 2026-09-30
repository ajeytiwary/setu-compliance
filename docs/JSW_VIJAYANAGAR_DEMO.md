# JSW Vijayanagar HRC → EU — Demo Guide

**Demo ID:** `JSW-VIJAYANAGAR-HRC-EU-2026` · **Server:** `http://localhost:8765` · **Duration:** 30–45 min

> **Honesty header (read first on the call).** Shipment identifiers (`JSW-HRC-NL-001` …),
> counterparties, tonnages, invoice values and margins are **synthetic demo rows** shaped like a
> Vijayanagar BF-BOF → caster → hot-strip-mill HRC flow. Regulatory context (CBAM tables, steel
> safeguard categories under 2026/1384 + 2026/1457, EU–India FTA status) comes from configured
> source snapshots. This demo does **not** claim access to JSW private SAP/MES/EMS and does **not**
> claim to be deployed by JSW Steel. Publicly substantiated facts live in `docs/PUBLIC_CASE_STUDY.md`
> (2.80 MnT FY26 exports, 66.8% Europe, 1.13 MnT HRC, EPD `EPD-IES-0005172:001`, plant-wise
> accounting + accredited verifiers per company reporting).

## Files

| File | Purpose |
|------|---------|
| `examples/jsw_vijayanagar_demo_portfolio.json` | 8 synthetic shipments, €7.79 M bound, NL/DE/IT/BE/FR/ES/PL |
| `examples/jsw_vijayanagar_cbam_actual.json` | Versioned CBAM actuals payload (1.73 tCO₂e/t, mirrors `cbam_actual_steel.json`) |
| `scripts/load_jsw_demo.py` | Loader: backbone samples + JSW canonical rows + shipments + supplier wiring |

## Setup (before the meeting)

```bash
cd /home/plasmion/git/setu-market-access-mvp-production
PYTHONPATH=. .venv/bin/python scripts/load_jsw_demo.py
# re-runnable; use --reset to clear JSW-% rows first (demo DB only)

PYTHONPATH=. nohup .venv/bin/python -m uvicorn app.main:app --port 8765 >/tmp/setu_server.log 2>&1 &
curl -s localhost:8765/api/dashboard | head -c 200
.venv/bin/python -m pytest -q
```

## Shipment map (what each row proves)

| Shipment | Route | Scenario | Proves |
|----------|-------|----------|--------|
| `JSW-HRC-NL-001` | Rotterdam, 72083900, 2500 t, €1.70 M | READY_CANDIDATE | Hero: close blockers live, pipeline CBAM assembles |
| `JSW-HRC-DE-002` | Hamburg, 72083800, 1800 t, €1.22 M | CBAM_VERIFICATION | CALCULATED_UNVERIFIED vs VERIFIED |
| `JSW-HRC-IT-003` | Genoa, 72083900, 1200 t, €0.82 M | QUOTA | Cat 1A, `QUOTA_BALANCE_REQUIRED` — never hallucinated |
| `JSW-PLATE-BE-004` | Antwerp, 72085120, 900 t, €0.68 M | QUOTA | Cat 7, India order `09.9856` country-quota path |
| `JSW-SS-IT-005` | La Spezia, 72191390, 600 t, €1.05 M | REACH_SVHC | Cat 8 stainless (`09.9862`), value-weighted risk |
| `JSW-HRC-FR-006` | Dunkirk, 72083900, 1500 t, €1.02 M | PRECURSOR_EMISSIONS | VERIFIED precursor vs DEFAULT share |
| `JSW-HRC-ES-007` | Valencia, 72084000, 1100 t, €0.75 M | ORIGIN_EVIDENCE | FTA preview passes technically, `CURRENT_MFN` legally |
| `JSW-HRC-PL-008` | Gdansk, 72083900, 800 t, €0.55 M | GENEALOGY | Missing heat/slab/coil link + evidence-request loop |

## Live script (8 steps)

### 0 — Landing (2 min)
```bash
curl -s localhost:8765/api/dashboard | python3 -m json.tool | head -30
```
**Say:** "€7.79 M synthetic JSW-shaped book. One tile is real regulation, the rest is revenue at risk until evidence lands."

### 1 — Risk drilldown (4 min)
```bash
curl -s localhost:8765/api/market-access/risk-drilldown | python3 -m json.tool | head -60
```
**Say:** "`CONNECTED_SHIPMENT_DATA`. Italy/Spain/Netherlands at risk by named shipment with blocker counts. Click into `JSW-HRC-NL-001`."

### 2 — Hero shipment by human number (3 min)
```bash
curl -s localhost:8765/api/shipments/JSW-HRC-NL-001 | python3 -m json.tool | head -40
```
**Say:** "Ops quotes `JSW-HRC-NL-001`, not UUIDs. Every route resolves both."

### 3 — Pipeline CBAM: SAP → MES → EMS → math (6 min)
```bash
curl -s -X POST localhost:8765/api/pipeline/steel/JSW-HRC-NL-001/cbam | python3 -m json.tool | head -40
curl -s -X POST localhost:8765/api/cbam/calculate -H 'Content-Type: application/json' \
  -d "{\"payload\": $(cat examples/jsw_vijayanagar_cbam_actual.json)}" | python3 -m json.tool | head -30
```
Expected: pipeline assembles SAP SD + 2 MES edges + EMS activity; versioned `EU_CBAM_2026_2547`,
specific 1.73 tCO₂e/t direct-only, `CALCULATED_VERIFIED` (VERIFIED pack) vs `CALCULATED_UNVERIFIED`
for `JSW-HRC-DE-002`.
**Say:** "Same canonical facts feed the passport and the export pack. The EPD is environmental
evidence — never asserted as the CBAM number."

### 4 — Steel safeguard: quota truth (4 min)
```bash
curl -s -X POST localhost:8765/api/regulatory/steel/evaluate -H 'Content-Type: application/json' \
  -d '{"payload":{"cn_code":"72083900","origin_country":"IN","import_date":"2026-09-29","quantity_t":2500,"customs_value_eur":1700000}}' | python3 -m json.tool
curl -s -X POST localhost:8765/api/regulatory/steel/evaluate -H 'Content-Type: application/json' \
  -d '{"payload":{"cn_code":"72085120","origin_country":"IN","import_date":"2026-09-29","quantity_t":900,"customs_value_eur":680000}}' | python3 -m json.tool | grep -E 'category|order_number|entitlement'
```
Expected: `1A` + 50% out-of-quota, `QUOTA_BALANCE_REQUIRED`; plate shows `09.9856`.
**Say:** "Category mapping is live. The balance comes from the Commission QUOTA database at
clearance — we surface the order number, never the tonnes remaining."

### 5 — FTA preview: potential only (3 min)
```bash
curl -s -X POST localhost:8765/api/fta/origin/evaluate -H 'Content-Type: application/json' \
  -d "{\"payload\": $(cat examples/fta_origin_preview.json)}" | python3 -m json.tool | head -20
```
Expected: `CURRENT_MFN`, `preference_available: false`.
**Say:** "Concluded 2026-01-27, not in force. Technical preview passes; legal guardrail blocks booking."

### 6 — Supplier loop + remediation (5 min)
```bash
curl -s localhost:8765/api/suppliers | python3 -m json.tool | head -30
curl -s -X POST localhost:8765/api/market-access/shipments/JSW-HRC-PL-008/simulate-remediation \
  -H 'Content-Type: application/json' -d '{"requirement_code":"GENEALOGY","estimated_cost":4000}' | python3 -m json.tool
```
**Say:** "Verify-once/share-many: one VERIFIED ferroalloy evidence covers NL-001 and FR-006.
What-if never touches the ledger."

### 7 — DPP + declaration pack (4 min, close with trust)
```bash
curl -s localhost:8765/api/shipments/JSW-HRC-NL-001/dpp | python3 -m json.tool | head -30
curl -s -X POST localhost:8765/api/customs/declaration-readiness -H 'Content-Type: application/json' \
  -d '{"payload":{"shipment_ref":"JSW-HRC-NL-001","cn_code":"72083900","origin_country":"IN","import_date":"2026-09-29","customs_value_eur":1700000,"quantity_t":2500}}' | python3 -m json.tool | head -30
```
**Say:** "Schema.org JSON-LD, `MVP_READINESS`, blockers embedded. `READY_FOR_SUBMISSION` means our
gates pass — customs/CBAM/verifier acceptance stays external. That boundary is the product."

## Objection one-liners

| Objection | Answer |
|-----------|--------|
| "Is this JSW data?" | "No — synthetic rows shaped like the public Vijayanagar route. Your SAP/MES/EMS extracts replace them in the pilot." |
| "Is the CBAM number real?" | "The 1.73 math is versioned 2025/2547 arithmetic on demo activity; the EPD is never asserted as CBAM." |
| "Where is the quota balance?" | "Behind the Commission login. Order number + category today, live balance on day one." |
| "When does the FTA save money?" | "At entry into force. Until then MFN-clean and preview-ready." |
| "What do you need for a pilot?" | "SAP SD + MES genealogy + EMS activity extracts, one verifier contact, one EU importer EORI. `docs/12_WEEK_PLAN.md`." |

## Pilot scoping checklist

- [ ] Confirm 2–3 real CN codes + routes (benchmark granularity)
- [ ] List SAP/MES/EMS export formats vs `connectors/connector-contracts.json`
- [ ] Name the verifier (maps to `CBAM_VERIFICATION` + verification pack)
- [ ] EU importer EORI + customs broker
- [ ] Agree seed scope: 1 real shipment + public JSW case side-by-side
- [ ] Sign data-processing note: pilot DB client-isolated; demo DB stays synthetic
