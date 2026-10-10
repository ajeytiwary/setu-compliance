# Client demo readiness — 5 October 2026

## Verdict

**Ready for a guided, explicitly synthetic client demonstration of the dossier control flow. Not ready to claim general client-PDF ingestion or production CBAM filing readiness.** Open `/dossier-demo` from the pilot app. The presenter needs two pilot identities in the same tenant: a contributor and an independent verifier. Keep both tokens private. The seven initial PDFs and two corrected versions are bundled, marked synthetic, and versioned.

## Reproduced journey

1. Create a dossier from seven synthetic PDFs. Initial decision: BLOCKED for seven pending reviews, wrong MTC heat, and unverified CBAM data.
2. Download a PDF and inspect its extracted fields, item rows, page, line, bounding box where available, and SHA-256. Review the seven originals as the separate verifier. Decision stays BLOCKED on MTC heat and CBAM verification.
3. As contributor, replace the MTC and CBAM report PDFs. Review both new versions as verifier. Decision becomes READY. Prior versions and their events remain.
4. The calculation shown is `(1500 + 100 × 0.5) / 1000 = 1.55 tCO₂/t`; `1.55 × 2.252 = 3.4906 tCO₂` for the shipment. The page labels arithmetic provisional while the dossier is BLOCKED and displays source, audit-chain and decision-snapshot integrity separately.

The Playwright run completed the full browser journey with zero console errors, zero HTTP errors, and no desktop or mobile horizontal overflow. Screenshots are in `docs/qa/`. The API regression suite verifies independent review, tenant isolation, hashes, historical versions, graph edges, arithmetic, audit chain, and tamper detection.

## Controls tightened for this preflight

READY now requires the invoice, PO, origin, destination, CN, net weight and container identifiers in every document, item rows in invoice/packing/SAD, positive amounts and weights, and agreement between EUR invoice and SAD customs value. The source provenance is re-parsed and compared on read and review. A PDF whose bytes do not match its stored digest cannot be downloaded. Evidence links in the UI identify document roles instead of opaque UUID prefixes; shipment tonnage comes from the parsed invoice.

## Boundary before a real client pilot

The one-click dossier seed accepts only the generated fixture PDFs. Real MTC, SAD, shipping-bill, invoice and CBAM layouts still need annotated gold examples, measured extraction accuracy per field and row, exception review, and a tested upload-to-graph path. OCR can recover image-only text but cannot yet establish reliable heat/coil or CBAM table facts across arbitrary scans. The event hash chain is internal to SQLite; it is tamper-evident against accidental changes, not an externally anchored immutable audit log. A READY demo state means the synthetic control set passed. It is not regulatory approval.
