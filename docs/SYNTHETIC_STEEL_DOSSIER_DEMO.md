# Synthetic steel dossier demonstration

Open `/dossier-demo` from the pilot app. This is a **synthetic, labeled product demonstration**. All nine PDFs are generated from `scripts/build_demo_dossier.py` into `data/demo_dossier/`; `manifest.json` records their SHA-256 hashes. The documents imitate the field structure of an India→Belgium steel export and import chain without representing a real company, shipment, customs declaration, or verification opinion.

## Workflow

1. Sign in with a pilot contributor token and create the synthetic dossier. The API stores seven PDF versions, parses their field and item-row text, and records a source hash and page/line/bounding-box reference where unambiguous.
2. The initial decision is **BLOCKED**. The MTC says `DEMO-HEAT-WRONG` while the invoice and packing list say `DEMO-HEAT-20376`. The installation report says `UNVERIFIED` and has no verifier report reference. All documents also start `PENDING` review.
3. Use a **different** verifier identity to review the original PDFs. The decision stays BLOCKED on the heat and CBAM verification blockers.
4. Use a contributor identity to replace the MTC and CBAM PDFs with the corrected synthetic versions. The old files, hashes, approvals, and event history remain. Both new versions start PENDING.
5. Use the verifier identity to review the corrected PDFs. The decision becomes **READY** for this synthetic demonstration only.

`POST /api/dossiers/demo` creates a tenant-scoped dossier. `GET /api/dossiers/{id}` returns the active and historical PDF versions, fact and row provenance, evidence links, blockers, CBAM calculation, immutable-style event chain, and integrity status. The review and remediation endpoints require pilot roles; a submitter cannot approve their own PDF version. PDFs can be retrieved through authenticated, tenant-scoped endpoints.

## Calculation and lineage

The CBAM result uses the existing `calculate_actual_steel` engine and its `EU_CBAM_2026_2547` methodology. The synthetic installation reports 1,500 tCO₂ direct emissions, 100 t precursor at 0.5 tCO₂/t, and 1,000 t activity. Specific embedded emissions are `(1,500 + 100 × 0.5) / 1,000 = 1.55 tCO₂/t`. For a 2.252 t shipment, the demonstrated embedded amount is `3.4906 tCO₂`. No EUR certificate liability is asserted because the demo has no real carbon-price, free-allocation, or certificate snapshot.

Each mutation appends an event with actor, timestamp, payload, previous hash and event hash. Decision snapshots persist the active PDF IDs, evidence edges, blockers, calculation input hash and result. Reads re-hash the PDF bytes, re-parse source facts and rows, verify the event chain, and compare the latest decision snapshot with the active documents. Any mismatch blocks READY.

The model gateway is optional for this demonstration. The configured `deepseek/deepseek-v4-flash` endpoint produced one citation-checked line from the synthetic invoice in 45.1 seconds after reducing output budget and using a configurable, bounded timeout. The deterministic dossier path does not wait for a model call.

## Verified checks and remaining boundary

The authenticated end-to-end API test covers tenant isolation, source-PDF download/hash equality, independent reviewer actions, BLOCKED→remediation→READY, exact CBAM arithmetic, graph edges, audit hash-chain integrity, and a forged parsed-field negative case. The generated MTC was rendered and visually inspected; its synthetic notice and mismatched heat are legible. The page JavaScript bundles with Bun. A live Chrome Interceptor check is unavailable because the Interceptor CLI is not installed in this environment.

The one-click seed accepts only bundled synthetic PDFs. Arbitrary real MTC, SAD, shipping-bill, and CBAM layouts still require their own annotated gold fixtures and parser work before this can be presented as a general client-document ingestion service. READY must always be described as a synthetic demo state, never a filing or verifier approval.
