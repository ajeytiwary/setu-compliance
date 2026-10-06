# PDF Inspector public corpus evaluation — 2026-10-04

## Scope and method

I ran the repository's `ingest_pdf` function against ten locally stored PDFs from the user-supplied Scribd list and checked whether each file fits the configured model adapter limits. I visually checked the Star Pipe invoice and read layout-preserving text from its matching C1 annexure, the packing list, and the Vardhman bill of lading. I then called `propose_pdf_lines` on the Star Pipe invoice using the configured `deepseek/deepseek-v4-flash` endpoint. This is a sample evaluation, not a measured accuracy score for all 27 links. The original Chandan Belgium MTC PDF (ID 916073792) is not in the local corpus.

## Measured pipeline results

| Scribd ID | Role | Pages | Deterministic shipment lines | Deterministic time (ms) | Model input status |
|---|---|---:|---:|---:|---|
| 975352350 | Star Pipe export invoice | 1 | 0 | 146.3 | Eligible |
| 975352347 | Matching tax invoice | 1 | 0 | 91.6 | Eligible |
| 975352352 | Matching customs C1 | 1 | 0 | 57.1 | Eligible |
| 800499484 | Star Pipe packing list | 2 | 0 | 164.0 | Eligible |
| 800499503 | Matching ISF | 1 | 0 | 46.1 | Eligible |
| 574284615 | Vardhman India→Italy B/L | 2 | 0 | 86.6 | Eligible |
| 1028478834 | JSW MTC | 2 | 0 | 258.9 | Eligible |
| 1069041631 | Indian shipping bill | 7 | 0 | 699.5 | Eligible |
| 768736623 | CBAM installation workbook PDF | 348 | 0 | 12,767.9 | Rejected: `PDF_PAGE_LIMIT_EXCEEDED` (12-page cap) |
| 725614266 | India→EU SAD/DV1 | 2 | 0 | 47.3 | Eligible |

All ten returned `PDF_LINE_ASSOCIATION_UNVERIFIED`. The rule accepts only one text line containing explicitly labeled CN/HS, QTY, unit, currency, and value in a fixed order. Actual PDF tables place column labels and cells on different lines. The result is a **0/10 document-level shipment-line recall** on this sample. This is not a field-level accuracy estimate: no field predictions were produced. The model request for ID 975352350 returned `LLM_REQUEST_OR_RESPONSE_FAILED` / `ReadTimeout` after the configured 45-second timeout; there were no model predictions to score. The adapter does not include `processing_time_ms` on failure, so the duration cannot be recovered from its result alone.

## Independently checked source facts and linkage oracle

| Document | Facts visible in source | Expected relationship |
|---|---|---|
| Export invoice 975352350 | Invoice `SPR2526E1692`, 03-01-2026, container `TGHU6127284`, origin India, destination United States, HS `73071120`, 214 pieces, net 17,360.77 kg, gross 18,710.78 kg, USD 30,670.32 | Same shipment as tax invoice and C1 below; **non-EU** |
| Tax invoice 975352347 | Invoice `SPR2526E1692`, container `TGHU6127284` | Match by invoice and container; INR and USD values require a documented rate before comparing |
| Customs C1 975352352 | Invoice `SPR2526E1692`, container `TGHU6127284`, 45 packages, gross 18,710.78 kg, net 17,360.78 kg | Match shipment, but flag **0.01 kg net-weight discrepancy** against export invoice |
| Packing list 800499484 | Invoice `SPR2425E1523`, container `MSMU8565268`, 25 numbered item rows across 2 pages, 1,375 pieces, net 17,809.19 kg, gross 18,889.20 kg, 36 crates, United States | Link to ISF below; do not join to the 2026 invoice |
| ISF 800499503 | Invoice `SPR2425E1523`, container `MSMU8565268`, Houston destination | Match packing list; **non-EU** |
| B/L 574284615 | B/L `SLDH00054055`, Vardhman→Sideria Italy, invoices `COM210000154` and `COM210000155`, containers `MSDU1239509` and `UETU2626377`, HS `72283029`, 53,265 kg, PO `31171` | Genuine India→EU transport evidence; **must not** link to either Star Pipe group |

These PDFs do not form one complete shipment chain. The strongest EU-bound B/L and the strongest invoice/C1 group belong to different companies, years, products, and shipments. Joining them would fabricate provenance. The Star Pipe groups are useful negative CBAM fixtures, not positive India→EU steel imports. The packing list also has `ITEM CODE` values that are not HS/CN codes; mapping those twelve-digit item identifiers to CN would be a serious table interpretation error.

## Correctness and pilot readiness

1. **Extraction is currently blocked on real PDF tables.** `app/document_lines.py` emits no candidates for the sampled invoice, packing list, C1, B/L, MTC, shipping bill, SAD, or CBAM PDF. The model adapter is only a candidate generator; the live endpoint timed out on the invoice. A client cannot use the present PDF route to ingest these documents end to end.
2. **The data model is too narrow for the proposed corpus benchmark.** `app/document_lines.py` and `app/llm_document_ingest.py` support shipment-line fields, but not PO, MRN, EORI, shipping bill number, gross weight, package count, item code, MTC certificate number, material grade, CBAM installation/process/precursor/emissions fields, or multiple invoices and containers on one B/L. Therefore a complete field extraction or evidence graph score cannot be produced from the current response schema.
3. **Provenance is incomplete for PDFs.** The code records a PDF page and text line only for accepted candidates, with `bbox: null`; it does not preserve a PDF table cell, column, or bounding box. Model citations are checked against extracted text, but a matching quote does not prove correct cell/row geometry. The invoice row association and the 25-row packing list need geometry-aware table extraction and visual review coordinates.
4. **Normalization needs separate typed values and source literals.** The invoice shows `17,360.77` and `30,670.32`; the numeric parser currently accepts only numbers without grouping commas. Dates such as `03-01-2026` are rejected unless already ISO formatted. Quantity in pieces and weight in kg are distinct measures and must not be conflated. HS `73071120` is an Indian export code, not automatically a validated EU TARIC classification.
5. **Linkage and reconciliation need explicit rules.** Build document nodes, field observations, and asserted edges keyed by issuer, invoice, container, date, and shipment role. Record exact source spans and conflicts such as the 0.01 kg difference. Require human resolution before an edge can support calculations or READY status. Negative joins must be tested as strongly as positive joins.
6. **The model service is not pilot reliable in this run.** A single short invoice timed out after 45 seconds. Add timeout/error telemetry, bounded retry or asynchronous queueing, idempotency by file digest, and a persistent review task. Do not silently treat timeout as an empty document. The 348-page CBAM PDF needs page selection or document segmentation before model use.
7. **No CBAM calculation or full evidence-graph claim was validated here.** With zero extracted lines, the pipeline cannot reach a meaningful calculation or READY decision from these PDFs. A positive EU invoice→packing list→B/L→MTC→SAD→CBAM installation fixture is still needed to test that path.

## Recommended acceptance gate

Create a manually annotated gold set with source-page and bounding-box coordinates for a representative selection of these PDFs. Score field exact match, typed normalization, row and table association, positive and negative document edges, conflict detection, and wall-clock processing time separately. Require the Star Pipe US documents to remain blocked for EU import use, the Vardhman B/L to remain separate, and the 0.01 kg discrepancy to appear as a resolvable conflict. A passing unit test suite alone is insufficient: the targeted tests passed **12/12**, while all ten real PDFs yielded zero deterministic shipment lines.

Sources: [Star Pipe export invoice](https://www.scribd.com/document/975352350/SPP-ExportInvoice-SPR-502423), [Star Pipe matching tax invoice](https://www.scribd.com/document/975352347/SPP-ExportTaxInvoice-SPR-502427), [Star Pipe C1](https://www.scribd.com/document/975352352/SPP-ExportInvoiceAnnexureC1-SPR-502426), [Star Pipe packing list](https://www.scribd.com/document/800499484/SPP-ExportPackingList-SPR-291367), [Star Pipe ISF](https://www.scribd.com/document/800499503/SPP-ISF10Plus2-SPR-291372), [Vardhman B/L](https://www.scribd.com/document/574284615/Bill-of-Lading-SLDH00054055).
