# Regulatory change feed pilot

## Product boundary

This is a private, authenticated **pull feed** for a single-tenant pilot deployment. It is not yet an email/webhook service or a contractual real-time feed. The implemented product-level matcher handles normalized TARIC measure rows only. A source hash change in CBAM, EUCDM, sanctions or another dataset does **not** claim that a specific CN code or shipment changed. The older development-only `/api/regulatory/change-impact` queue broadly flags all legacy shipments and must not be sold as precise impact analysis.

## Customer flow

1. A contributor creates a watch with an eight-digit CN code and two-letter origin: `POST /api/regulatory-feed/watches` with `{"cn_code":"72083900","origin_country":"IN","label":"Hot rolled coil"}`. `GET /api/regulatory-feed/watches` lists active watches. Deleting a watch disables future matching while preserving historical events.
2. Run a validated TARIC sync on the **same application deployment and database** that holds the watchlists. Either `python scripts/sync_sources.py --dataset taric_measures --file <official-export.csv> --as-of YYYY-MM-DD --force` for a full official export, or the positional auto sync for a delta ZIP. The first full snapshot establishes the comparison baseline; the next full snapshot produces ADDED/REMOVED/UPDATED measure events. Delta ZIPs produce only ADDED row events because they are not full state snapshots; removals cannot be inferred from two deltas.
3. `GET /api/regulatory-feed/events?since=YYYY-MM-DD` returns tenant-scoped events. `as_of=YYYY-MM-DD` filters out measures whose effective start is later than the requested date. `GET /api/regulatory-feed/events.csv?since=YYYY-MM-DD` exports up to 1,000 events for a weekly human-reviewed digest. Both require a pilot bearer token. `GET /api/regulatory-feed/status` reports observed TARIC snapshot age with a 48-hour operational target.
4. A contributor can `POST /api/regulatory-feed/events/{id}/reviews` with `{"disposition":"ACKNOWLEDGED","reason":"Reviewed against import entry and quota"}`; reviews append an actor and timestamp without rewriting the event. Each event contains the changed normalized row before and after, source URL, old/new SHA-256 snapshot IDs, effective start, CN and origin. The watch match is a *review prompt*: measure conditions, additional codes, documents, quota balances, and customs acceptance need separate evaluation. Origin geography codes that are neither a two-letter country nor an explicit all-origin label need a validated mapping before they can produce a product-level alert.

## Production operations and failure handling

The GitHub Actions sync validates and commits source snapshots, but its runner has no customer watchlist database. It cannot deliver customer events. The application deployment must run the sync against its persistent database, or reconcile committed snapshots through an equivalent controlled job. Configure a scheduler, verify daily success and `status=FRESH`, and alert the operator when stale, missing, `UNCOMPARABLE`, or sync failure occurs. No customer-facing refresh SLA should be sold until a measured run history and alert escalation exist.

A correction is another validated source publication, not an edit of an event. Keep both snapshots and append the resulting event; record the operator's explanation in the customer review record. Before promising the weekly digest, test baseline→change→CSV with a licensed source export and a pilot tenant on the hosted app, including backup and restore of watches and events. Feed data follows the same private backup policy as dossier data.

## Source rights register (pilot review required)

| Dataset | Current route | Authority in config | Pilot reuse decision |
| --- | --- | --- | --- |
| TARIC measures | Official export or third-party mirror delta | Varies by manifest | Use official source for legal conclusions. Record distribution terms and attribution before delivering derived alerts; do not redistribute the mirror ZIP. |
| CBAM defaults and benchmarks | TAXUD workbooks | Official | Source-linked internal calculation only until workbook-specific reuse is checked. |
| EUCDM | Softdev mirror ZIP | Mirror | Internal schema comparison only; no product-level feed from it yet. |
| Eurostat Comext | Eurostat API | Official statistics | Dataset-specific notice and attribution review before customer exports. |
| ECHA Candidate List and SCIP | Official or mirror/manual | Varies | Do not include in a resale feed until a source-specific rights decision is recorded. |
| Client documents | Private tenant uploads | Customer | Never include in a cross-client feed without explicit contract authority. |

For every enabled source, the commercial owner must record the exact distribution URL, terms/version, attribution wording, allowed redistribution, reviewer, and review date. A public URL or GitHub code licence does not by itself grant rights to resell data.
