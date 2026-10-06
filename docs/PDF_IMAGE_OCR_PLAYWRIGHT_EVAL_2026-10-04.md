# PDF image OCR and browser evaluation — 2026-10-04

## Image OCR comparison

I compared the text-layer path with Tesseract on rendered PDF pages (`pdftoppm`, 170 DPI, Tesseract sparse-text mode 11). OCR returns word confidence and pixel boxes mapped to PDF page coordinates; visual row lines are reconstructed by vertical position. OCR is limited to 3 pages, 8 MB, and bounded subprocess time. All OCR output is **REQUIRES_REVIEW** and cannot create verified CN classifications or READY evidence.

| Public PDF | Text layer | Image OCR | Assessment |
|---|---|---|---|
| Star Pipe export invoice `975352350` | Full item row and six key literals; ~100 ms pypdf extraction | Invoice/container/HS/weight/value recovered in ~3.2–3.4 s. Bounding-box grouping reunites `73071120`, `214`, `17,360.77`, `30,670.32` on one row, although OCR adds trailing punctuation to the amount. | Prefer text layer for exact values; OCR can cross-check geometry. Tesseract page mode 6 missed the row, so mode 11 is used. |
| Star Pipe packing list `800499484` | All 25 item codes and rows across two pages; ~0.2 s text extraction | 22/25 item codes, no spurious item codes, ~5.7–6.0 s. Missing `829351512617`, `829351800516`, `829351803983`. Invoice, container and totals remain visible. | Text layer is more complete and much faster. OCR cannot replace its item table. |
| JSW scanned MTC `903558901` | One nonbreaking-space character; unusable | ~1,352 OCR characters, 236 words, ~2.0–2.3 s. Certificate and `Heat No.` heading visible, but heat/coil table cells remain noisy and cannot be trusted as identifiers. | OCR is materially better than the absent text layer, but requires manual or stronger table-cell verification. Increasing render resolution to 300 DPI did not reliably recover the heat/coil cells. |

The inspector now runs image OCR automatically when text-layer extraction is unusable. A **Compare image OCR** checkbox runs it alongside a healthy text layer. The selected source stays `pypdf`/`pdftotext` when text is available; OCR is chosen only for an image-only PDF. The UI exposes OCR timing, confidence, line text and boxes. Long numbers in the scanned MTC are **not** presented as CN hints.

## Playwright visual inspection

Playwright was added to `.venv` using `uv pip install` because the Python package was absent; browser binaries were already cached. The browser run used the local app and two distinct pilot identities.

- Created the synthetic dossier: **BLOCKED** on pending reviews, wrong MTC heat, and missing CBAM verification.
- Downloaded an authenticated source PDF.
- Reviewed the seven original PDF versions as a separate verifier: still **BLOCKED** on the two genuine demo discrepancies.
- Replaced MTC and CBAM PDFs as contributor, reviewed replacements as verifier: **READY**, `1.55 tCO₂/t`, `3.4906 tCO₂` for the shipment.
- Desktop and 390 px mobile had no document-level horizontal overflow. Console errors: **0**. HTTP errors: **0**.
- The OCR comparison page selected Tesseract for scanned `903558901` and pypdf for clean `975352350`, with **0** page errors.

Playwright exposed two UI bugs that were fixed: review clicks could race the response, and an OCR-panel newline caused a JavaScript syntax error. The dossier now disables an action while its request runs, and its document details collapse into a usable summary view at READY.

Screenshots: [initial BLOCKED](qa/dossier-blocked.png), [READY](qa/dossier-ready.png), [mobile READY](qa/dossier-mobile.png), [OCR comparison](qa/pdf-ocr-comparison.png).

## Decision

Keep a **hybrid path**: text layer first for born-digital PDFs; image OCR for scans and optional comparison; no automatic release from OCR text. OCR improves recoverability, not field authority. A production scanned-MTC parser still needs annotated heat/coil cell boxes and a stronger OCR/table model before those identifiers may support evidence edges.
