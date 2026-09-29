# Version-aware EU market-access compiler

Setu's regulatory core is intentionally separated from generic UI.

## First-wave engines

1. **EU Steel Trade Measure v2** — Regulation 2026/1384 + Implementing Regulation 2026/1457. The engine maps CN → product category, resolves origin/order number, consumes fresh QUOTA balances and calculates the 50% out-of-quota additional duty. The repository snapshot contains verified mappings used by the public steel case; the engine accepts a complete official Annex export and fails closed for a CN not present in loaded official data.
2. **CBAM Definitive v2** — 2025/2547 actual-emissions engine plus importable corrected 2025/2621+2026/1740 default values and 2025/2620 benchmarks/free-allocation adjustment. Reference annex numbers are data, not hard-coded guesses. Missing corrected defaults, benchmark or CSCF blocks the affected calculation.
3. **CBAM Verification Pack** — 2025/2546 + 2025/2551 lifecycle across monitoring plan, operator emissions report, verification report, findings, reasonable assurance and verifier accreditation validity.
4. **Regulation lifecycle** — every registered rule carries legal_basis, version, published_at, effective_from/to, status, jurisdiction, product_scope, source and calculation_version. Negotiated instruments cannot become claimable merely because a scenario rule exists.

## Operational output

`POST /api/customs/declaration-readiness` compiles TARIC + QUOTA + steel trade measure + CBAM verification evidence into `READY_TO_DECLARE` or `BLOCKED`, with required TARIC document codes and calculated customs liability where resolvable.

## Reference-data policy

Large official annex tables are imported as versioned data. Setu does not invent missing tariff, quota, benchmark, default-emission or legal-effective-date values. A missing dataset produces a blocker. This is deliberate: executable compliance must fail closed.

## Second wave

PPWR; REACH/SCIP; richer live TARIC/trade-defence ingestion; sanctions/ownership screening; customs valuation; proof-of-origin lifecycle. These should reuse the same lifecycle schema and declaration-readiness compiler rather than creating independent dashboard labels.
