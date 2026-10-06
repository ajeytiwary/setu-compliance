# Public-document intake validation — 5 October 2026

## Result

A real-document upload-to-candidate-evidence-graph path is implemented at `/real-dossier`. A contributor can upload PDFs or a CBAM communication XLSX, inspect source-cited extraction, and ask a separate verifier to approve or reject each source. Documents, hashes, extracted observations, review actors, and hash-linked events persist by tenant. The graph proposes links on exact invoice identity and checks container and weight conflicts. A separate reviewer must explicitly approve or reject each link with a written reason; approval is refused while a linked pair has an unresolved source-value conflict. It deliberately stays **BLOCKED** until a complete, verified same-shipment EU steel dossier is established. Approval of a document means its source and observations were reviewed; it does not make an unrelated collection READY.

## Public benchmark corpus

The source PDFs are kept outside git. They were already present in the sibling `scribd` downloader directory; the path named `scribdto` was absent. The [Scribd downloader](../scripts/fetch_public_corpus.sh) and source list can reacquire them from preview-accessible pages. The [gold annotations](../data/public_corpus/gold.json) include source URLs, expected roles, 38 selected fields, and 12 selected table cells. The European Commission's [communication page](https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism/cbam-communication-and-news_en) provides a populated steel workbook example, extracted from its example ZIP. It is a **2024 historical example**, suitable for parser regression, not a 2026 verified installation declaration.

| Source | Role in test | Critical observations |
|---|---|---|
| [Chandan steel certificate](https://www.scribd.com/document/916073792/4-316L-50-45-24-LOT27792) | MTC | Invoice `EXP/23-24/01244`, PO `102833`, heat `CH-20376`, HS `7222.11`, 2,252 kg; one heat/grade/size row |
| [Indian customs shipping bill](https://www.scribd.com/document/1069041631/333156818052026INAPL6SB22200520261616) | Shipping bill | SB `3331568`, 18 May 2026, UK destination; not Chandan's shipment |
| [India→Spain DV1/SAD case](https://www.scribd.com/document/725614266/DV1-Import-SAD) | Educational case | Invoice/B/L/TARIC/EORI/weights; **not an actual filed SAD** and not steel |
| [Star Pipe export invoice](https://www.scribd.com/document/975352350/SPP-ExportInvoice-SPR-502423) and [matching C1](https://www.scribd.com/document/975352352/SPP-ExportInvoiceAnnexureC1-SPR-502426) | Positive link and conflict | Invoice `SPR2526E1692`, container `TGHU6127284`; invoice net 17,360.77 kg vs C1 net 17,360.78 kg; US destination |
| [Vardhman B/L](https://www.scribd.com/document/574284615/Bill-of-Lading-SLDH00054055) | Negative link | Italy-bound steel B/L with different invoices and two containers; must stay separate |
| [Commission populated steel workbook](https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism/cbam-communication-and-news_en) | XLSX cell extraction | Installation name and four actual product CN/SEE rows from `Summary_Products`, with sheet/cell addresses |

## Measured extraction

The reproducible command is:

```sh
PYTHONPATH=. .venv/bin/python scripts/evaluate_public_corpus.py --corpus-dir "$EUROSETU_PUBLIC_CORPUS_DIR" --cbam-workbook "$EUROSETU_PUBLIC_CORPUS_DIR/cbam-steel-blast-furnace-example.xlsx"
```

On these six Scribd PDFs: **38/38 selected field values**, **12/12 selected row cells**, **36/38 field hits with page + line + quote**, and **23/38 with an unambiguous bounding box**. The two row tables and the MTC heat row carry a source page and quote; not every cell has a box. The benchmark found exactly the expected Star Pipe invoice→C1 candidate link, did not join the Vardhman B/L, and flagged the 0.01 kg net-weight conflict. The workbook parser found the installation name and all four selected product SEE totals by exact cell. Per-document processing times and source SHA-256 values are in [the machine-readable score](qa/public-corpus-score.json).

These are **selected-field recall and selected-row-cell checks** on known layouts. They are not precision, generalisation accuracy, authenticity assessment, or a passing rate for arbitrary client PDFs. The shipping bill's six item lines, a genuine populated EU SAD, scanned MTC heat/coil, and 2026 verified CBAM installation data remain unmeasured or unavailable in this corpus. A blank SAD template cannot fill that gap. The model gateway is optional and did not supply any benchmark answer.

## End-to-end behavior and production boundary

The authenticated API test uploaded the six PDFs plus the Commission XLSX into one tenant dossier. It persisted seven nodes, proposed only the Star Pipe invoice↔C1 link, detected the weight conflict, and ended BLOCKED after seven independent document reviews. An explicit approval of the conflicted link returned `UNRESOLVED_SOURCE_CONFLICT`; an explicit rejection was persisted and audited. Cross-tenant access was denied. Parsed JSON tampering changed integrity to failed; malformed and oversized files are rejected. Reads verify stored file hashes, the parsed-data digest attached to the upload audit event, and that document/link review states agree with their review events. A forged link approval is detected as `REVIEW_AUDIT_MISMATCH`. The browser flow uploaded and reviewed the Star Pipe pair at desktop and mobile widths with no console errors, HTTP errors, or horizontal overflow.

The graph is a **candidate graph**. It does not yet support reviewer-edited field corrections, manual edge resolution, a real complete dossier release policy, an external immutable audit anchor, or asynchronous processing for large PDFs. A real client pilot should begin with a consented same-shipment corpus and a field/row gold set, then require an independent reviewer to resolve discrepancies before calculation or READY. This implementation is a reliable intake and exception-review starting point; the synthetic dossier remains the only demonstrated READY workflow.
