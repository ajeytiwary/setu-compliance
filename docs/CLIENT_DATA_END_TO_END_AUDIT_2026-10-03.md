# Client PDF pipeline audit — 2026-10-03

## Verdict

**Not ready for a client pilot that relies on PDF-only ingestion or automated `READY` decisions.** The repository has working, tested domain components and a PDF text-extraction batch, but no connected end-to-end path from these 35 PDFs to validated shipment lines, calculations, evidence edges, and replayable decisions. A bounded CSV-led pilot with human-verified document evidence remains the credible route.

## What ran

- Ran `.venv/bin/python scripts/extract_client_data.py --force` on all 35 PDFs in `data/client_data` with pypdf and pdftotext; PaddleOCR was disabled. The script wrote local sidecars, `_index.json`, `_candidates.csv`, and `_receipts.csv`.
- Ran `PYTHONPATH=. .venv/bin/pytest -q tests/test_extract_client_data.py tests/test_document_ingest_receipts.py tests/test_pipeline.py tests/benchmarks/test_client_data_chaos.py`: **32 passed**. This verifies components and synthetic cases, not field accuracy on the 35 PDFs or their path to a decision.
- Parser timing recorded in sidecars totals **89.2 seconds** across pypdf and pdftotext calls; the slowest individual parser call was **22.4 seconds**. This excludes process startup, file writes, OCR, review, and downstream computation. No end-to-end latency metric exists.

## Measured ingestion results

| Measure | Result |
| --- | ---: |
| PDFs labelled `ok` | 35/35 |
| More than 100 extracted characters | 33/35 |
| At least one apparent eight-digit CN | 25/35 |
| A parsed quantity | 13/35 |
| A parsed EUR value | 4/35 |
| CN, quantity, EUR value and origin together | 2/35 |
| Typed receipt rows | 0 |

`ok` means a parser returned any text, even one whitespace character. It is not a document-quality or field-accuracy result. The prior `_index.json` listed only one document before this run; consumers of a cached index can silently operate on an incomplete batch.

## Field-by-field trace

| Requested field | Current result on PDF path |
| --- | --- |
| Invoice number | Present in some text, but not extracted into the shipment candidate or CSV. |
| HS/CN | Regex accepts any eight-digit pattern and picks the first; no label, row, product, or authoritative classification check. Example: `scribd-1047251010` picks `10880007` from an IEC number; its item CN is `40111010` (tyres). |
| Heat/coil | No PDF candidate field or heat → slab → coil linkage. Requires MES data under the pilot contract. |
| Weight | Regex searches whole document and picks the maximum. It does not distinguish kg, tonnes, gross/net, line/total, or item association. Example: `scribd-1047251010` records `6716.641` as tonnes although the PDF labels it **KGS**. |
| Value/currency | Only EUR-prefixed amounts are recognized; the maximum is selected, with no invoice/FOB distinction or line association. USD invoice `scribd-797969813` has no value candidate despite a visible USD total. |
| Origin | `IN` is inferred from any India-related text, including ports; it is not tied to a goods-origin declaration or line. |
| Container/B/L | Container is detected only as a PII regex and redacted in previews. No structured container or B/L link is emitted. |
| Table cell accuracy | The text parsers flatten tables. The receipt parser handles receipt-shaped pipe/CSV blocks, but produced zero rows for this corpus. No cell-level accuracy benchmark exists for these PDFs. |
| Row association | The PDF candidate combines first CN, largest quantity and largest EUR amount across a whole document. No shared row key, invoice line, or cross-document join is enforced. |
| Page/bounding box | Neither candidates nor receipt records include page number or bounding box. A document SHA prefix and receipt row index are insufficient to navigate to the source cell. |
| Processing time | Per-parser milliseconds are recorded; per-field, per-document total, queue time, OCR time and end-to-end decision latency are absent. |

The `scribd-797969813` export invoice is for a buyer in the **United States**, contains three distinct HS lines, a USD total, an invoice number and container number. The extractor returns the first HS as its single candidate, no quantity and no EUR value. It cannot represent this invoice accurately or decide EU applicability. The one-character `scribd-903558901` is still marked `ok=True`.

## Calculation and evidence path

The PDF batch stops at sidecar files. `_candidates.csv` has six columns (source, CN, quantity, EUR value, origin, parser); it lacks invoice, line, destination, date, currency, heat, container, B/L and provenance coordinates. There is no batch step that validates these rows, creates canonical transactions/evidence, invokes the CBAM/TARIC engines, and persists linked decisions. Therefore **no calculation or evidence graph was produced from this corpus**, and correctness of PDF-derived calculations cannot be claimed.

The separate `app/steel_pipeline.py` assembles canonical SAP/MES/EMS/supplier/verifier records. It does not consume these PDF sidecars. Its CBAM path requires genealogy and activity; missing inputs block. The v1 API can store transactions, evidence and decisions with pinned references, but its transaction model does not require nonzero value/quantity or a confirmed CN, and its check API accepts caller-supplied obligations. These interfaces need a trusted compiler gate before any PDF-derived `READY` can be client-facing.

The evidence lifecycle and synthetic chaos tests demonstrate blocking and predecessor-linked remediation, but do not prove a PDF field → page/cell → claim → obligation → calculation → decision trace. A user cannot yet click from a failed decision to the exact PDF cell, correct it, and replay the same snapshot.

## Architecture and production priorities

1. **P0 — Establish a reviewed transaction line schema.** Store raw value, normalized value, unit/currency, document SHA-256, document type, invoice and line IDs, extraction method/version, confidence, page and bounding box for every field. Require destination, date and product classification before scope or duty evaluation. Treat missing or conflicting fields as `BLOCKED`.
2. **P0 — Build and test the actual PDF-to-decision orchestration.** Classify documents; extract line tables; join invoice, shipping bill, packing list, B/L and MTC by explicit IDs; validate weights, totals, currency and origin; attach evidence; invoke date-pinned TARIC/CBAM; persist a replayable decision. Reject cross-row and cross-document combinations without a documented join.
3. **P0 — Create a manually adjudicated gold set from representative PDFs.** Include exact invoice, HS/CN, heat/coil, weight/unit, value/currency, origin, container/B/L, cell text, page and box. Report precision/recall and row-join accuracy separately. The 35 PDFs are heterogeneous public Scribd documents, not a verified single-client shipment pack; obtain client-owned pilot data and permission before treating them as customer truth.
4. **P0 — Add fail-closed quality gates.** Reject one-character/low-text parses, OCR failure, non-EU destinations for EU decisions, unrecognized currencies, impossible units and unverified CNs. Preserve OCR and text-layer alternatives without overwriting better results on a later run. The present `--force` without Paddle replaced a previously useful Paddle parse of `scribd-1048968752` with one character.
5. **P1 — Harden operations.** Immutable raw uploads in tenant-scoped encrypted storage; malware/type/size checks; asynchronous bounded workers; idempotent jobs and retries; per-stage latency and error telemetry; retention/deletion controls; authorization checks on evidence/decision reads; snapshot pinning; backup/recovery and load testing on realistic page counts. Benchmark throughput with OCR enabled before promising a service level.

## Pilot gate

Before showing a client a PDF-driven decision, require a single complete shipment pack with independently verified line truth, source-cell navigation, reproducible calculations against pinned reference data, and a demonstrated `BLOCKED → corrected evidence → READY` replay where both decisions and changed evidence hashes remain accessible. Until then, describe the current output as **candidate extraction for human review**.
