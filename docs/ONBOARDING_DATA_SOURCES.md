# EuroSetu Onboarding — Data Sources, Features, Workflows: How to Run Everything

**Audience:** new engineer / pilot operator who wants to run every dataset, feature, and workflow locally and know what is real vs synthetic.
**Honesty header (read first):** Commercial rows (invoices, values, shipments like `HRC-NL-001`, `STEEL100-001`) are **synthetic demo data**. Regulatory tables (CBAM defaults/benchmarks, steel safeguard categories, TARIC snapshots) are **official EU publications** with SHA-256 provenance. EuroSetu is engineering assurance, not legal certification.

Repo root in this guide: `/home/plasmion/git/eurosetu-market-access-mvp-production`

---

## 0. One-time setup (5 min)

```bash
cd /home/plasmion/git/eurosetu-market-access-mvp-production
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install openpyxl   # official CBAM XLSX parsing
```

Verify:

```bash
PYTHONPATH=. .venv/bin/python -c "import app.main; print('app imports OK')"
.venv/bin/python -m pytest tests/ -q -m "not scale"   # expect ~154 passed
```

Key rule: engines consume **normalized contracts only**, never vendor URLs directly. Replacing a provider = config/adapter change, never an engine rewrite (see `docs/DATA_SOURCE_ARCHITECTURE.md`, `docs/SOURCE_ONBOARDING.md`).

---

## 1. The four-layer mental model

| Layer | What it is | Registry | Can I redistribute? | How it is tested |
|-------|------------|----------|---------------------|------------------|
| **L1 — Regulatory goldens** | EC CBAM filled examples, defaults, benchmarks, operator guidance + BF/BOF worked example, TARIC | `config/public_evidence_sources.json` (ids `ec_*`, `taric`) + `config/data_sources.json` (datasets `cbam_defaults`, `cbam_benchmarks`, `cbam_examples`, `taric_measures`, `steel_2026_1457`) | **No — link + hash only** | `tests/benchmarks/test_eu_cbam_golden.py`, `test_cbam_2026.py`, `test_taric_live.py` |
| **L2 — Public real-world** | UCI steel telemetry (35,040 obs), DocILE/CORD/QUEST docs, worldsteel LCI, voestalpine EPDs, COMEXT, UN Comtrade, Terlouw Steel_CBAM | `config/public_evidence_sources.json` (ids `uci_*`, `docile`, `cord_*`, `quest_*`, `worldsteel_*`, `voestalpine_*`, `eurostat_*`, `un_comtrade`, `terlouw_*`) | Per-license; record URL+sha256, never scrape landing pages/APIs | `scripts/probe_public_sources.py` health check; adapters map into canonical contracts |
| **L3 — Competitor scenarios** | Steelforce / Spaeter / CBAMReturn workflow shapes, re-implemented synthetically | ids `carbonchain_*`, `cbamreturn_*` | Scenario metadata only; never copy vendor files | `tests/benchmarks/test_steelforce_style.py`, `test_spaeter_style.py`, `test_carbmee_supplier.py`, `test_client_data_chaos.py` |
| **L4 — Synthetic corrupted packs** | Deterministic offline evidence room + CHAOS derivatives | Built by scripts below into `data/public_trade_evidence/` (gitignored, regenerable) | Yes (we generated it) | `tests/test_public_evidence_corpus.py`, `test_steel_100_demo.py`, `test_client_data_chaos.py` |

Provenance schema on every artifact: `source_type / source_url / license / retrieved_at / sha256 / original_filename / synthetic_transform / parent_artifact / expected_use`. See `EU-STEEL-EXPORT-2026/provenance.json`.

---

## 2. Every data source — what it is, license, how to use/test it

### 2a. Layer 1 — Authoritative regulatory goldens (NORMATIVE oracles only)

| # | Registry id | What you get | URL | License / redistribution | EuroSetu use → feature/workflow | How to run / test |
|---|-------------|--------------|-----|--------------------------|---------------------------------|-------------------|
| 1 | `ec_cbam_examples` | 7 filled CBAM communication-template XLSX (steel BF, steel EAF, screws/nuts) | `https://taxation-customs.ec.europa.eu/document/download/8d00a979-e57d-4e53-a11f-8b01370236a9_en?filename=Communication-template-examples.zip` | EU reuse terms; **do not redistribute** | CBAM ingestion + precursor chains | `python scripts/sync_sources.py --dataset cbam_examples` then `pytest -q tests/benchmarks/test_eu_cbam_golden.py` |
| 2 | `ec_cbam_defaults` | Definitive default values XLSX (corrected 2025/2621 + 2026/1740) | TAXUD `DV+correcting+act_final_update_06.08.xlsx` (see registry for full URL) | EU reuse terms | CBAM math (country sheets, route `(A)/(C)`, 10% 2026 markup) | `PYTHONPATH=. .venv/bin/python scripts/sync_official_reference_data.py` → `scripts/convert_official_to_imports.py` → `data/cbam/defaults.csv` (11,469 rows). Test: `test_cbam_2026.py` |
| 3 | `ec_cbam_benchmarks` | Benchmark reference XLSX (2025/2620) | TAXUD `CBAM+Benchmarks_20260206.xlsx` | EU reuse terms | Installation intensity priors | Same pipeline → `data/cbam/benchmarks.csv` (570 rows). Test: `test_cbam_2026.py` |
| 4 | `ec_cbam_operator_guidance` | Operator guidance PDF + BF/BOF worked example | `https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism_en` | EU reuse terms; local copy gitignored under `docs/` | Reconstruct installation → processes → products → embedded emissions | Manual read + link/hash in manifest; exercised by `test_eu_cbam_golden.py` |
| 5 | `taric` / dataset `taric_measures` | CN → measures, restrictions, documents; quota balances | `https://taxation-customs.ec.europa.eu/online-services/online-services-and-databases-customs/eu-customs-tariff-taric_en` + mirror `https://github.com/rousseauxy/taric-opendata` | EU reuse terms | `POST /api/customs/taric/resolve` → `customs_liability_eur`; missing/stale → `QUOTA_BALANCE_REQUIRED` (fail-closed) | `python scripts/sync_sources.py taric_measures eucdm` ; `pytest -q tests/benchmarks/test_taric_live.py` |
| 6 | dataset `steel_2026_1457` | 30-category / 337-CN steel safeguard table (2026/1384 + 2026/1457) | `https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32026R1457` | LEGAL (EUR-Lex) | `POST /regulatory/steel/evaluate` | Checked in at `data/eu_steel_categories_full.json`; rebuild via `scripts/fetch_steel_quota_table.py` (see `docs/SOURCE_SYNC.md`) |
| 7 | dataset `eucdm`, `quota_balances`, `echa_candidate_list`, `scip_schema`, `eu_sanctions` | EUCDM code lists, quota DB, Candidate List, SCIP 6.10, FSF sanctions | See `config/data_sources.json` | OFFICIAL / MIRROR per provider | Customs, REACH/SCIP, sanctions gates | `python scripts/sync_sources.py --list` then `--dataset <name> --file <browser-download>` for WAF-blocked publishers |

> Only **direct authoritative expected outputs** are NORMATIVE oracles. Competitor numbers are never goldens.

### 2b. Layer 2 — Public real-world documents & data (real inputs, provenance required)

| # | Registry id | What you get | URL | License | EuroSetu use | How to run / test |
|---|-------------|--------------|-----|---------|--------------|-------------------|
| 8 | `uci_steel_energy` (+ `uci_steel_energy_zip` direct ZIP) | 35,040 obs: kWh, reactive power, CO₂, load, time — DAEWOO Steel Gwangyang | landing page + direct ZIP `https://archive.ics.uci.edu/static/public/851/steel+industry+energy+consumption.zip` (verified HTTP 200, ~482 KB, inner `Steel_industry_data.csv`) | CC BY 4.0 (attribute Sathishkumar V E, Shin, Cho 2021; DOI 10.24432/C52G8C) | EMS/plant telemetry → evidence/calculation | `--acquire` downloads + hashes the ZIP into `data/public_trade_evidence/originals/uci_steel_energy_zip/`; room builder maps real columns (Usage_kWh → energy_kwh, Lagging+Leading kVarh → reactive_kvarh, CO2 → co2_t, Load_Type → load_type) into `EU-STEEL-EXPORT-2026/CARBON/energy_meter.csv` (2,000 real rows, FAC-01..25 round-robin) + `energy_meter_meta.json` (column map + parent sha256). Chain: plant telemetry → emissions evidence → CBAM installation workbook → product → shipment |
| 9 | `docile` | 6,680 annotated + 100k synthetic + ~1M unlabeled business docs; invoices/orders + line items | `https://docile.rossum.ai/` (+ `https://github.com/rossumai/docile`) | Dataset-specific; verify before acquisition | Document ingestion / invoice-PO extraction accuracy | Manual/license review only — builder never scrapes. Probe: `python scripts/probe_public_sources.py` |
| 10 | `cord_receipts` | 1,000 annotated receipts | `https://github.com/clovaai/cord` | CC BY 4.0 | Receipt/invoice extraction | Same as above — adapter maps to `COMMERCIAL_INVOICE` evidence type. Typed records land via `app.document_ingest.extract_receipt_records` (pipe/CSV tables → one record per row, raw cell kept beside the parsed value, ambiguous amounts named not guessed) |
| 11 | `quest_tables` | 954 annotated business-document tables | via DocILE GitHub | Dataset-specific | Table-structure extraction (invoice/PO lines) | Same — maps to line-item evidence |
| 12 | `worldsteel_lci` | 2026 LCI: 160+ sites, 356 Mt, 16 products; eco-profiles direct, detail on request | `https://worldsteel.org/steel-topics/life-cycle-thinking/life-cycle-inventory-lci-study/` | Dataset-specific | BF/BOF vs EAF intensity priors | Room copy: `CARBON/facility_emissions.csv` (25 facilities, BF-BOF 1.73 / EAF 0.38). Cite as Layer-1-adjacent prior, not a CBAM certificate |
| 13 | `voestalpine_epds` | Real steel EPD PDFs (heavy plate, HR strip, CR strip) | `https://www.voestalpine.com/group/en/group/environment/environmental-product-declarations/` | Public PDFs; verify reuse | EPD/PCF evidence docs linked to heat/batch/facility | Room manifests: `CARBON/epds/manifest.csv` + pointer `CARBON/epds/epd_sources.json` (link only — no PDF copied/redistributed). Guardrail: EPD stored as environmental evidence only, never mapped into `cbam.embedded_emissions` without CBAM-methodology data |
| 14 | `eurostat_comext` | EU import/export by commodity/country/month | `https://ec.europa.eu/eurostat/web/international-trade-in-goods/database` | Eurostat reuse policy | Realistic India→EU steel portfolio distributions | API adapter (`comext_trade` dataset); probe only, no bulk scrape |
| 15 | `un_comtrade` | Trade flows: HS, value, quantity, partner | `https://comtradeapi.un.org/public/v1/preview/C/A/HS` | UN terms of use | Same — transaction value/quantity priors | Same — preview API only |
| 16 | `terlouw_steel_cbam` (+ `terlouw_steel_cbam_zenodo` direct ZIP) | Steel_CBAM research dataset/code (2025, J. Cleaner Production) — repo `steel_cbam_assessment/{data,figs,logs,results,notebooks 0-5,config.py,db_functions.py,functions.py,mapping.py,plotting.py,regionalization.py}` | paper `https://doi.org/10.1016/j.jclepro.2025.145000` + data DOI `10.5281/zenodo.17236022` + direct ZIP `https://zenodo.org/api/records/17236022/files/tomterlouw/Steel_CBAM-v.1.0.0.alpha.zip/content` (verified, 18.5 MB, 86 files) | BSD-3-Clause (code+data); paper via publisher | Regional production + prospective LCA for carbon accounting — research priors only, never a normative oracle | `--acquire` downloads + hashes the ZIP into `data/public_trade_evidence/originals/terlouw_steel_cbam_zenodo/`; room builder writes `CARBON/research/terlouw_steel_cbam_summary.json` (record structure + README head + parent sha256). Chain: UCI telemetry → emissions evidence → installation workbook (Terlouw = regional/LCA priors) → product → shipment |

FUNSD (199 noisy forms) is intentionally **excluded** from the primary corpus — licensing/use restrictions (noted in `docs/dataset_example_resources.md`).

### 2c. Layer 3 — Competitor-derived scenarios (workflow shapes, COMPETITIVE-SCENARIO label)

| # | Registry id | Public case | What we take from it | EuroSetu benchmark | How to run |
|---|-------------|-------------|----------------------|---------------------|------------|
| 17 | `carbonchain_steelforce` | Steelforce: multi-CN, multi-country, multi-supplier CBAM workflow | 100–500 txns, 15 CNs, 8 suppliers, 5 countries → ingest→classify→applicability→installation→join→validate→calculate→BLOCK→remediate→READY→export | `STEELFORCE-STYLE-001` (`test_steelforce_style.py`, 500 lines, 20% fault injection, 100% hard faults at txn level) | `pytest -q tests/benchmarks/test_steelforce_style.py` |
| 18 | `carbonchain_spaeter` | Spaeter: CBAM ops + commercial decision | Scenario-analysis variant | `test_spaeter_style.py` | `pytest -q tests/benchmarks/test_spaeter_style.py` |
| 19 | `cbamreturn_worked_example` | Messy supplier files: `FINAL v3 (2)`, `Instalation name`, `16,50000`, `1.9 tCO2e/t`, 10-digit TARIC, kg-tonne, TOTAL rows, unsaved formulas | All 15 chaos patterns | `CLIENT-DATA-CHAOS` CHAOS-001..015 (see §5) | `pytest -q tests/benchmarks/test_client_data_chaos.py` |

Never copy vendor files verbatim; patterns are re-implemented synthetically.

### 2d. Layer 4 + local connectors/examples (what you actually execute)

| Source | Path | How to use |
|--------|------|------------|
| Base synthetic corpus | `data/public_trade_evidence/evidence_room/` (100 txns, 50 suppliers, 590 evidence, 25 faulted) | `python scripts/build_public_evidence_corpus.py --clean` (add `--acquire` for direct-file downloads only) |
| Evidence room 2026 | `data/public_trade_evidence/EU-STEEL-EXPORT-2026/` (ERP/LOGISTICS/QUALITY/CARBON/REGULATORY/expected/provenance) | `python scripts/build_evidence_room_2026.py --clean [--transactions N] [--ems-rows M]` |
| Source health | `data/public_trade_evidence/source_probe.json` | `python scripts/probe_public_sources.py` (HEAD→Range GET, never full scrape) |
| 14 connector samples | `connectors/samples/` (`sap_sd/mm`, `mes_genealogy`, `ems_activity`, `scada_ems`, `supplier_cbam`, `verifier`, `gst_invoice`, `icegate_shipping_bill`, `dgft_coo`, `lims`, `logistics`, `oracle_erp`, `tally_export`) | `POST /api/integrations/canonical/import` per code, or bulk via `app/integrations.py:import_sample` (demo guide loads 14/14) |
| 6 example portfolios | `examples/` (`client_portfolio_12_shipments.json`, `jsw_*`, `cbam_actual_steel.json`, `fta_origin_preview.json`) | `POST /api/shipments` with portfolio; JSW profile via `scripts/load_jsw_demo.py` |
| Live regulatory sync | `data/raw/`, `data/normalized/`, `data/manifests/` | `python scripts/sync_sources.py` (auto 5) / `--dataset/--all/--file/--url/--force` (weekly/manual) / `--strict` (CI) |
| Messy-data use cases | `use_cases/ouco_mtc_messy/` (OUCO link-only catalog + synthetic messy MTC/receipts → BLOCKED → READY) | `.venv/bin/python use_cases/ouco_mtc_messy/run_messy_demo.py` then `pytest -q tests/test_use_cases_messy.py` |

> Note on the OUCO link: `https://ouco-industry.com/material/to` resolves (HTTP 200) to the "Top 10 China Marine Crane Manufacturers in 2023" ranking page — logos/crane photos only, **no mill certificates or receipts**. The use case catalogs those images link-only and replays MTC/receipt messiness synthetically (seed 20261002).

---

## 3. Build the corpus (copy-paste)

```bash
# Layer 4 base (offline, deterministic seed 20261002)
python scripts/build_public_evidence_corpus.py --clean
# → evidence_room/{transactions.csv (100), suppliers.csv (50), evidence.json (590), fault_truth.json (75 READY/25 BLOCKED)}

# Layer 4 evidence room (requires base first)
python scripts/build_evidence_room_2026.py --clean
# → EU-STEEL-EXPORT-2026/{ERP,LOGISTICS,QUALITY (manifest + synthetic EN 10204 3.1 sample_mtc 10 rows, shape-note),CARBON (energy_meter 2000 REAL UCI rows + energy_meter_meta.json, facility_emissions 25, research/terlouw_steel_cbam_summary.json, epds/epd_sources.json),REGULATORY,corrupted_derivatives.json (25),expected/{initial (75/25),remediation_actions,final (100/0)},provenance.json (25 entries, 4 layers; Layer-2 artifacts carry ACADEMIC_OPEN_DATA/PUBLIC_COMPANY source_type + parent sha256)}

# Optional: download direct official files only (never scrapes landing pages/APIs)
python scripts/build_public_evidence_corpus.py --clean --acquire
# → originals/{ec_cbam_examples (.zip 8.1 MB), ec_cbam_defaults (.xlsx), ec_cbam_benchmarks (.xlsx), uci_steel_energy_zip (.zip 482 KB), terlouw_steel_cbam_zenodo (.zip 18.5 MB)} + manifest.json acquired_originals=5 (each with sha256 + retrieved_at)

# Health-check all 19 registry URLs (no bulk download)
python scripts/probe_public_sources.py
# → data/public_trade_evidence/source_probe.json (expect 19× HTTP 200)
```

Scale knobs: `--transactions N --ems-rows M` on the room builder. Corpus targets (roadmap): 1,000 txns, 200 invoices/POs, 100 packing/customs, 50 workbooks/MTCs, 30 EPDs, 25 facilities, 50 suppliers, 35k+ EMS rows, versioned TARIC/regulation, 200+ broken / 50+ clean chains.

---

## 4. Evidence-room tour (`EU-STEEL-EXPORT-2026/`)

```
ERP/            sales_orders.csv, purchase_orders.csv, suppliers.csv
LOGISTICS/      invoices/manifest.csv, packing_lists/manifest.csv, customs_declarations/manifest.csv
QUALITY/        mill_test_certificates/manifest.csv + sample_mtc_en10204_31.csv (10 synthetic EN 10204 3.1 rows, heat-linked) + shape_note.json (public plate certs = shape reference only, never copied)
CARBON/         energy_meter.csv (2,000 REAL UCI rows, CC BY 4.0) + energy_meter_meta.json (column map + parent sha256), facility_emissions.csv (BF-BOF 1.73 / EAF 0.38),
                cbam_supplier_templates/manifest.csv, epds/manifest.csv + epds/epd_sources.json (voestalpine link-only pointer), verification/manifest.csv,
                research/terlouw_steel_cbam_summary.json (Zenodo 17236022, BSD-3-Clause, 86 files — research priors, never normative)
REGULATORY/     taric/ cbam/ sanctions/ (versioned snapshots)
corrupted_derivatives.json   25 rows, each with parent_artifact_sha256 + chaos_id
expected/       initial_decisions.json (75 READY / 25 BLOCKED, €12.8m total),
                remediation_actions.json (6 actions), final_decisions.json (100 READY)
provenance.json 25 entries, layers=[regulatory-goldens, public-real-world, competitor-scenarios, synthetic-corrupted] (Layer-2: energy_meter* = ACADEMIC_OPEN_DATA/CC BY 4.0, terlouw summary = ACADEMIC_OPEN_DATA/BSD-3-Clause, epd_sources = PUBLIC_COMPANY/link-only)
```

Chains to trace: **plant-telemetry → evidence → workbook → product → shipment** and **PO → invoice → packing → customs → CN/TARIC → MTC → heat → facility → EPD → workbook → verification → graph**.

---

## 5. CHAOS-001..015 family (every case: BLOCKED → remediated → READY)

| ID | Defect | Evidence state |
|----|--------|----------------|
| CHAOS-001 | Renamed worksheets (`Installation Data` → `Sheet1 FINAL v3 (2)`) | UNVERIFIED |
| CHAOS-002 | Decimal comma (`1,9` parsed as 19) | UNVERIFIED |
| CHAOS-003 | Units in cells (`1.9 tCO2e/t`) | UNVERIFIED |
| CHAOS-004 | kg–tonne error (1925 kg as 1925 t, ×1000) | UNVERIFIED |
| CHAOS-005 | 8-digit CN where 10-digit TARIC required | MISSING |
| CHAOS-006 | Stale cached Excel formula | STALE |
| CHAOS-007 | Duplicate supplier (one entity, two ids) | CONFLICTING |
| CHAOS-008 | Conflicting installation IDs | CONFLICTING |
| CHAOS-009 | Missing precursor section | MISSING |
| CHAOS-010 | Wrong reporting period | EXPIRED |
| CHAOS-011 | Expired verification statement | EXPIRED |
| CHAOS-012 | Superseded MTC, no active replacement | SUPERSEDED |
| CHAOS-013 | Duplicate invoice number | CONFLICTING |
| CHAOS-014 | Invoice/PO quantity mismatch | CONFLICTING |
| CHAOS-015 | MTC heat-number mismatch | CONFLICTING |

Run: `pytest -q tests/benchmarks/test_client_data_chaos.py` (15 cases, each asserts BLOCKED → READY with predecessor + hash change via `evidence_lifecycle.evaluate_requirement` + `decision_engine.build_decision`).

---

## 6. Run every feature & workflow

### 6a. Server + demo (45–60 min client walkthrough — see `docs/CLIENT_DEMO_GUIDE.md`)

```bash
PYTHONPATH=. nohup .venv/bin/python -m uvicorn app.main:app --port 8765 >/tmp/eurosetu_server.log 2>&1 &
curl -s localhost:8765/api/dashboard | head -c 200
# UI: http://localhost:8765/   API docs: http://localhost:8765/docs   Benchmarks: http://localhost:8765/benchmarks
```

Load backbone → portfolio → evaluate (CBAM math on real Commission tables; quota returns `QUOTA_BALANCE_REQUIRED` until a live balance is supplied; FTA guardrail: EU–India `NEGOTIATED_NOT_IN_FORCE`):

```bash
# 14/14 connectors
PYTHONPATH=. .venv/bin/python -c "
from app.integrations import import_sample, integration_catalog
for c in integration_catalog()['connectors']: import_sample(c['code'])
print('14/14 imported')"
# 12-shipment portfolio → CBAM → steel safeguard → FTA preview → DPP → risk drilldown
# (full curl sequence in docs/CLIENT_DEMO_GUIDE.md §2g+)
```

### 6b. Benchmarks & tests (the full matrix)

```bash
# Corpus gates (determinism + 17-source registry + room layout 75/25)
pytest -q tests/test_public_evidence_corpus.py
# Flagship workflows
pytest -q tests/benchmarks/test_steel_100_demo.py tests/benchmarks/test_steelforce_style.py tests/benchmarks/test_client_data_chaos.py tests/benchmarks/test_spaeter_style.py tests/benchmarks/test_carbmee_supplier.py
# Regulatory goldens + fail-closed
pytest -q tests/benchmarks/test_eu_cbam_golden.py tests/benchmarks/test_cbam_2026.py tests/benchmarks/test_taric_live.py tests/benchmarks/test_fail_closed.py
# Everything (excluding scale)
.venv/bin/python -m pytest tests/ -q -m "not scale"
# Scale (opt-in, slow)
.venv/bin/python -m pytest tests/ -q -m "scale"
```

STEELFORCE-STYLE-001 acceptance: 100% hard faults surfaced at txn level, no clean record falsely BLOCKED, counts reconcile, export deterministic. STEEL-100-DEMO: 75 READY + 25 BLOCKED → remediation → 100 READY. Demo narrative: *100 txns → 27 BLOCKED → €3.8m blocked → 8 defects → 6 remediations → 100 READY* (room run reports €12.8m total — value depends on seed run; quote the `expected/` file you actually generated).

### 6c. Release + claims discipline

```bash
python scripts/release_benchmarks.py --skip-tests   # collects latest PASS per (suite,case) → web/benchmarks/<commit>/{results.json,summary.json} + releases.json
python scripts/lint_claims.py                        # forbids EU-certified / parity / guarantee language (must pass before release)
```

`/benchmarks` UI renders only released bundles. The **"Real-world evidence corpus"** section surfaces CLIENT-DATA-CHAOS (15) + STEEL-100-DEMO (1) alongside legal goldens.

---

## 7. Feature → data-source map (which data exercises which code)

| Feature / endpoint | Code | Data that drives it | Try it with |
|--------------------|------|---------------------|-------------|
| CBAM calculation | `app/cbam_definitive_v2.py`, `cbam_engine.py` | L1 defaults/benchmarks/examples; L2 UCI/worldsteel/Terlouw intensities; L4 supplier templates | `examples/cbam_actual_steel.json`, room `CARBON/` |
| TARIC measure stack | `app/taric_engine.py` | L1 TARIC snapshots + L2 COMEXT/Comtrade CN distributions | `POST /api/customs/taric/resolve` |
| Origin / FTA | `app/fta_origin.py` | L1 steel categories; FTA guardrail | `examples/fta_origin_preview.json` |
| Evidence lifecycle (7 states) | `app/evidence_lifecycle.py` (`VALID/STALE/EXPIRED/SUPERSEDED/CONFLICTING/UNVERIFIED/MISSING`) | L4 CHAOS derivatives; L2 EPDs/verification | `test_client_data_chaos.py`, `test_evidence_decay.py` |
| Decision engine (fail-closed) | `app/decision_engine.py` (`ERROR→BLOCKED→CONDITIONAL→READY`, `DECISION_POLICY_V1`) | All layers via obligations | `test_fail_closed.py`, room `expected/` |
| Supplier remediation loop | supplier/evidence-request endpoints | L4 supplier evidence | `POST /api/suppliers…`, `POST /api/remediation/…` |
| DPP / export package | compiler v2 | Canonical evidence graph | Demo guide §3+ |
| Benchmark harness | `app/benchmark_harness.py` (`compare/emit/assert_and_emit` → `benchmark_artifacts/`) | All suites in `specs/benchmark-suite.md §9.2` | Any `tests/benchmarks/test_*.py` |

---

## 8. Troubleshooting

| Symptom | Cause → fix |
|---------|-------------|
| `EADDRINUSE` / uvicorn exit 3/143 | Server already on 8765 — `lsof -i :8765` or reuse it; don't start a second one |
| Corpus test fails after manual edits | Rebuild: `build_public_evidence_corpus.py --clean && build_evidence_room_2026.py --clean` (deterministic; never hand-edit generated CSVs) |
| `acquire()` downloaded nothing | Expected for landing-page/API kinds — only `zip/xlsx/csv/json/xml` direct files download; rest need adapters/manual review |
| Probe shows non-200 | Upstream moved — update URL in `config/public_evidence_sources.json`, record new sha256, keep old provider disabled until equivalence checked |
| Quota returns `QUOTA_BALANCE_REQUIRED` | Correct fail-closed behavior — supply a fresh (≤1 day) QUOTA snapshot, never invent balances |
| Claim-lint fails | Remove EU-certified/parity/guarantee wording — "engineering assurance, not legal certification" |
| DB polluted between tests | `tests/conftest.py` autouse isolation — never remove it; demo DB `data/eurosetu.db` is gitignored |

---

## 9. Where to read next

- `docs/PUBLIC_TRADE_EVIDENCE_CORPUS.md` — corpus one-command use + provenance rules
- `docs/dataset_example_resources.md` — original four-layer research note (P0 table, STEELFORCE-STYLE-001 spec, CHAOS family)
- `docs/CLIENT_DEMO_GUIDE.md` — full 45–60 min click-by-click demo
- `docs/SOURCE_SYNC.md` — auto/weekly/manual sync pipelines
- `docs/DATA_SOURCE_ARCHITECTURE.md` + `docs/SOURCE_ONBOARDING.md` — trust classes (LEGAL/OFFICIAL/MIRROR/DEMO_ONLY) + provider replacement
- `docs/PILOT_DATA_CONTRACT.md` — minimum private integrations (SAP SD/MM, MES, EMS, supplier feed, verifier feed)
- `specs/benchmark-suite.md §9.2` — benchmark suite table
