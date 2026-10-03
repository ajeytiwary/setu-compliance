# Client-docs EU-bound use case (redacted derivatives, scenario demo)

**Honesty header:** this folder is a **scenario demo**, not a certification.
The 13 client PDFs under `data/client_data/` are **local only** (untracked,
never copied here). The two EU-bound shipments below are **hand-redacted
derivatives**: CNs, quantities, values, routes, and dates are kept; exporter/importer registration numbers, tax identifiers, bank accounts, seals,
container numbers, agent/job references,
personal names, and company legal names are dropped. The MTC heats are
**synthetic** (seed 20261003) shaped by the EN 10204 3.1 layout.

## Most relevant docs (of 13)

| Rank | Doc (local only) | Why |
|------|------------------|-----|
| 1 | `scribd-927038715.pdf` — Dadri ICD checklist, stainless bars/rods 72221119, 24.371 t, FOB EUR 47823.69, Antwerp → Germany | EU-bound **steel + CBAM in-scope** (category 14, order 09.9890). Exercises TARIC + steel safeguard + CBAM + valuation + origin. Primary case `CLIENT-AMBICA-01`. |
| 2 | `scribd-1047251010.pdf` — Hazira shipping bill, passenger tyres 40111010, 6.717 t, FOB EUR 15429.06, Hamburg → Budapest | EU-bound **non-steel / non-CBAM** contrast. Exercises TARIC + valuation + origin + PPWR/REACH/sanctions without steel/CBAM blockers. `CLIENT-APOLLO-01`. |
| 3 | `scribd-1048968752.pdf` — 1-page image MTC, EN 10204 3.1 flat HRC shape | **Evidence-quality shape** only (Egypt origin, not India): heat → chemistry/mechanical layout reused for synthetic MTC heats. |
| — | remaining 10 (US/CN/BD/EC/domestic) | Out of scope for EU market access; listed in `provenance.json` lineage only. |

## What the runner shows

`python use_cases/client_docs_eu_bound/run_client_docs_demo.py`

- Phase A (as-extracted): invoice UNPARSED, MTC without heat trace, no CBAM
  pack → evidence `UNVERIFIED`, decision **BLOCKED**, compiler **BLOCKED**.
- Phase B (remediated): verified evidence + heat-traced MTC + full CBAM
  verification pack → decision **READY**, compiler **READY_FOR_SUBMISSION**,
  entitlement **ENTITLED** (synthetic TARIC snapshot `as_of == import_date`,
  quota balance supplied — same injection pattern as
  `tests/test_active_entitlement.py`).
- Decisions chain via `predecessor_id` under `DECISION_POLICY_V1`.

Guardrail: READY/ENTITLED means EuroSetu rule/evidence gates pass.
Customs/CBAM/verifier acceptance remains external.
