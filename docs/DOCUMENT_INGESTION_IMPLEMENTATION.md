# Document ingestion implementation and pilot boundary

## Implemented

- CSV and XLSX/XLSM are read as source rows. Each mapped field retains filename, full SHA-256, sheet, row, column, raw value and cell address. Numeric parsing uses `Decimal`; kilograms convert to tonnes only with an explicit unit. EUR value is populated only for an explicit EUR currency.
- Invalid or missing CN, quantity, unit, value, currency, origin, destination, import date or invoice number generates named issues. USD/INR/GBP values require a pinned exchange-rate snapshot before a EUR customs value can be used. Non-EU destinations are blocked at compilation. Ragged CSV rows, duplicate headers, spreadsheet formulas and row/sheet limits are flagged.
- PDF text extraction is conservative: only an explicitly labelled CN/QTY/VALUE sequence on the same line becomes a review candidate. It retains page and text-line references and records that a bounding box is unavailable. Scans with insufficient text request OCR. Free-floating eight-digit numbers are never promoted to CN codes by the new decision path.
- The workflow parse endpoint returns `structured_ingestion` and its review candidates. The UI displays document issues and allows editing invoice, destination and required trade fields. Compile blocks unresolved ingestion issues and hard blockers, including missing EUR conversion or PDF bounding boxes.

## OpenAI-compatible model proposal path

The workflow website now has a pilot-only **Use a model to propose PDF fields** option and a model ID input. Its default is `deepseek/deepseek-v4-flash` at `http://172.17.0.1:8787/api/v1/chat/completions`. Operators can set `EUROSETU_INGEST_LLM_BASE_URL`, `EUROSETU_INGEST_LLM_MODEL`, and `EUROSETU_INGEST_LLM_API_KEY` on the server; the key is never returned to the browser. A model ID may be changed in the UI without changing the endpoint. Model calls require a pilot contributor or admin token, and use a 45-second timeout, page/text/line caps, and temperature zero.

The model must return raw field substrings with exact page, line, and quote citations. The server reopens the PDF text layer, checks each citation, and rejects unsupported fields or CN/quantity/value spread across unrelated rows. It then applies the same deterministic unit, currency, destination and missing-field checks as CSV/XLSX. Every PDF proposal remains review-only and carries `PDF_BOUNDING_BOX_UNAVAILABLE`, so it cannot turn into a submission-ready decision without layout provenance. The adapter accepts both standard and `data`-wrapped Chat Completions responses, as observed from the supplied gateway. JSON mode is used when available; a gateway rejection triggers one plain completion retry with the same validator.

## Verified

- On the 35 local public PDFs, the strict PDF extractor found **zero** self-contained labelled lines, flagged **two** as OCR-required, and flagged **all 35** as needing a verified row association. Its recorded parser time total was **59.9 seconds**. This is the correct fail-closed result for this heterogeneous corpus, not a claim of successful invoice extraction.
- The full repository suite with the model adapter passed **238 tests**. A live, synthetic gateway request using the supplied model produced one cited review candidate in **35.97 seconds**; no client data was sent. Focused model and website tests passed **11 tests**. Browser verification was attempted with the required Interceptor workflow, but the `interceptor` executable is unavailable in this environment; the UI was not visually verified.

## Remaining before a PDF-led client pilot

1. Add layout-aware OCR/table extraction that returns cell text, page and bounding box. Benchmark it against manually labelled invoice, shipping bill, packing list and MTC goldens; retain raw and normalized values.
2. Build explicit joins across invoice line, shipment, heat/coil, container and B/L. Reconcile totals and weights; prevent unrelated rows/documents from being combined.
3. Pin exchange rates, TARIC/source snapshots and evidence hashes; persist each correction and predecessor decision so users can navigate from blocker to source cell and replay.
4. Move parsing into tenant-scoped asynchronous jobs with bounded CPU/memory, retry/idempotency, retention controls and measured end-to-end latency. The current web endpoint parses synchronously and has an 8 MB upload limit.

The new code is a safer ingestion foundation. It does **not** establish production PDF extraction accuracy, a full evidence graph from PDFs, or automatic `READY` for this corpus.
