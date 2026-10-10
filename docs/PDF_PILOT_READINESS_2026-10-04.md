# PDF pilot readiness — 2026-10-04

## Implemented and verified

The `/workflow-run` upload route now exposes deterministic PDF observations with document SHA-256, literal source values, page/line references, bounding boxes when unambiguous, extracted table rows, processing time, and review status. The source text remains the authority; missing or repeated geometry is `null` rather than guessed.

Public fixture checks:

- Star Pipe export invoice `SPR2526E1692`: one invoice row with HS `73071120`, 214 pieces, 17,360.77 kg and USD 30,670.32. It creates one review candidate; no EUR value is invented.
- Star Pipe packing list `SPR2425E1523`: all 25 numbered item rows preserved across two pages. Its item codes are not classified as HS/CN.
- Star Pipe export invoice, tax invoice, and C1: three candidate document links on shared invoice and container; two conflicts record the C1 17,360.78 kg net weight against the invoices' 17,360.77 kg. Compile returns BLOCKED with `SOURCE_VALUE_CONFLICT`.
- Star Pipe packing list and ISF: linked on matching invoice/container. Vardhman India→Italy B/L is not joined to either Star Pipe group.
- HTTP `POST /api/workflow-run/parse` accepted the real PDF and returned the invoice table row; `GET /workflow-run` returned the observation UI. The embedded JavaScript bundled cleanly with Bun. The full Python test suite passed 242 tests.

## Remaining release blockers

This is a **reviewable pilot slice, not a production-ready client ingestion system**. Do not represent it as automatically verified or READY.

1. The current extraction rules cover a subset of text-layer invoices, packing lists, C1 forms, and B/L identifiers. Shipping bills, MTC heat/coil chains, SAD/MRN/EORI, and CBAM installation/precursor/emissions tables still need typed schema and annotated gold tests. Scans need OCR with geometry validation. The 348-page CBAM PDF exceeds the model adapter's 12-page limit and the upload tool's 8 MB limit.
2. Bounding boxes are available only for unambiguous text tokens. Repeated values and some container fields return no box. A geometry-aware cell model is needed before claiming complete page/bounding-box provenance or field-level extraction accuracy.
3. Cross-document reconciliation is in-session and candidate-only. A production evidence graph needs tenant-scoped persistence, immutable source versions, reviewer identity, signed resolution events, and server-side re-evaluation. The workflow compile API currently accepts browser-supplied lines and conflict state; it must never be treated as an authoritative release decision.
4. The configured OpenAI-compatible model endpoint timed out on the short public invoice in the live benchmark. Deterministic extraction runs without it; model reliability and fallback need load/timeout testing before a client depends on it.
5. No complete positive India→EU invoice→packing list→shipping bill→B/L→MTC→SAD→CBAM fixture is present in this corpus. The Star Pipe groups are US-bound negative cases, and the Vardhman B/L belongs to a different shipment. Thus CBAM calculations and READY status cannot be validated end to end from these files.
6. Interceptor, required by the local AGENTS.md for visual web verification, is not installed in this environment. HTTP and JavaScript checks passed, but a real Chrome visual pass remains open.

## Pilot gate

Before showing a client their own documents, assemble one permissioned complete EU shipment dossier with manually annotated fields and cells, run it through the parser and persisted evidence lifecycle, resolve discrepancies through an auditable review action, and demonstrate BLOCKED → remediation → READY with real versioned tariff, FX, and CBAM inputs. Keep synthetic demo data visibly separate.
