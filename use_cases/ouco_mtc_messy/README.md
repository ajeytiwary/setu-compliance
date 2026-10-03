# Use case: OUCO material page + mill-certificate messy-data demo

**Honesty header:** scenario demo only — not a certification, not a clearance
guarantee. Third-party content is **linked, never copied**.

## What the requested link actually holds (verified 2026-10-02)

- Requested: `https://ouco-industry.com/material/to`
- Resolves (HTTP 200) to: `https://ouco-industry.com/top-10-china-marine-crane-manufacturers-in-2023/`
  (canonical link confirms; `/material/to` is not a material-certificate page).
- Page content: "Top 10 China Marine Crane Manufacturers in 2023" ranking
  (ZPMC / WMMP / DHHI / Henan Mine / RHM / OUCO / GBM / THHI / Yuanwang /
  Great) + company logos and crane/factory photos. **No mill certificates,
  no MTC images, no receipts on this page.**
- `ouco_material_image_catalog.json` lists the page's content images as
  **links only** (no binaries copied). If you need actual material
  certificates, ask OUCO for their QA/cert page URL — this ranking page
  cannot supply them.

## What this demo shows with messy data + receipts

Public steel MTCs (e.g. hot-strip-mill EN 10204 3.1 certificates with a
chemical-composition block per heat and a mechanical-properties block per
batch) and CORD-style receipts arrive messy: decimal commas, units embedded
in numeric cells, heat numbers that disagree across documents, duplicate
supplier rows, duplicate invoices. This folder replays those shapes
**synthetically** (seed 20261002) through the real EuroSetu gates:

- `messy_mtc_input.csv` — 5 synthetic heat/batch rows, each carrying one
  receipt-style defect (decimal comma, embedded units, heat mismatch,
  duplicate supplier, duplicate invoice). Shape reference: public plate-mill
  MTC layout (heat → chemistry, batch → YS/TS/EL); no third-party document
  copied.
- `receipts_messy_sample.csv` — 4 CORD-shaped receipt lines with the same
  defect family at receipt level.
- `run_messy_demo.py` — parses each messy row, classifies via
  `app.evidence_lifecycle` (deterministic `as_of`), aggregates via
  `app.decision_engine` (`DECISION_POLICY_V1`, fail-closed):
  messy → `BLOCKED` naming the defect; remediated (clean twin row) → `READY`
  with predecessor link. Mirrors `CHAOS-002/003/007/013/015` without copying
  any vendor file. Also runs the typed receipt extractor
  (`app.document_ingest.extract_receipt_records`) over the receipts and
  prints the raw → parsed result, so the same defect family is shown twice:
  once as an evidence-state BLOCK, once as a parse-level named code.

## Run

```bash
cd /home/plasmion/git/eurosetu-market-access-mvp-production
.venv/bin/python use_cases/ouco_mtc_messy/run_messy_demo.py
.venv/bin/python -m pytest tests/test_use_cases_messy.py -q
```

## Provenance

Every synthetic derivative records `parent_source_url` (the OUCO page or the
public shape reference) + `synthetic_transform`. See `provenance.json`.
