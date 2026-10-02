# 12-week steelmaker pilot plan

## Goal
Connect one real India→EU steel flow from ERP/MES/EMS through versioned CBAM, origin/customs, evidence, DPP and shipment-level market-access readiness.

| Week | Objective | Exit criterion |
|---|---|---|
| 1 | Pilot boundary, security and data contracts | 10-30 representative EU shipments selected; owners and access approved |
| 2 | Live SAP SD/FI | ≥95% invoice-value reconciliation for selected shipments |
| 3 | SAP MM/PP + MES genealogy | ≥95% shipped-tonnage genealogy coverage from heat→slab→coil→shipment |
| 4 | EMS/SCADA + LIMS | Meter/activity and quality evidence mapped to production process |
| 5 | Supplier/precursor evidence | Required precursor suppliers represented with evidence status |
| 6 | CBAM calculation engine | Results reconciled against steelmaker compliance workbook; methodology version and inputs reproducible |
| 7 | Verifier workflow | Findings, evidence requests and verification status persisted |
| 8 | TARIC/current MFN + customs | Date/CN-specific customs treatment and required docs evaluated |
| 9 | EU-India origin readiness | BOM/origin inputs evaluable against authoritative PSRs when legally available; no premature FTA preference |
| 10 | ESPR/DPP outputs | DPP/readiness output generated from same canonical facts |
| 11 | Market-access economics | Real € order book, ready value, revenue at risk, CBAM exposure and remediation drilldown |
| 12 | Security, UAT and pilot sign-off | RBAC, audit, backup/restore, tests and customer acceptance completed |

## Acceptance criteria
- ≥95% ERP invoice-value reconciliation.
- ≥95% genealogy coverage by shipped tonnage.
- Every CBAM result reproducible from versioned inputs and methodology.
- Calculated vs independently verified status is explicit.
- 100% of blocking market-access verdicts explainable by rule + evidence lineage.
- ≥80% of evidence sourced automatically for the pilot scope.
- FTA savings are never booked unless the agreement/rule is effective for the shipment date.
- DPP, CBAM and export-package outputs derive from the same canonical data.
- Measurable reduction in manual compliance hours per shipment.
