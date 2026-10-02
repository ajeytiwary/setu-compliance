# EuroSetu CBAM 2026 Audit, Implementation Plan & Market-Access Evidence Passport

**Date:** 2026-10-01  
**Scope:** current `main` implementation plus branch `feature/cbam-2026-passport-plan`  
**Status:** engineering assessment, not legal certification.

## 1. Executive conclusion

EuroSetu already has a credible **steel-focused CBAM calculation core**, but it should not yet be marketed as a complete definitive-regime declaration engine. The strongest existing path is `app/cbam_definitive_v2.py`, not the older `cbam_engine.py` alone.

The 2026 hardening in this branch adds shipment-level **certificate-equivalent obligation**, free-allocation deduction, optional official certificate-price costing, explicit verification gating for actual emissions, and a fail-closed boundary around third-country carbon-price deductions.

The product opportunity is larger than CBAM: create a reusable **EU Market-Access Evidence Passport** that binds facility, product, supplier, shipment, regulation, evidence, verification and provenance into one permissioned record. CBAM then becomes one consumer of the passport alongside TARIC/customs, origin, steel trade measures, REACH/SCIP, PPWR and DPP.

## 2. Legal baseline used for this audit

The definitive CBAM regime applies from 1 January 2026. For non-electricity goods, embedded emissions may use actual emissions or the applicable Commission default values. Actual emissions used in the declaration require verification. The first annual declaration for 2026 is due by 30 September 2027. The 2026 certificate price is a quarterly average of EU ETS auction clearing prices. Free-allocation adjustment is governed by Implementing Regulation (EU) 2025/2620. Definitive-period default values are governed by 2025/2621 as corrected/amended, including 2026/1740.

Primary references:
- Regulation (EU) 2023/956 consolidated: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:02023R0956-20251020
- Implementing Regulation (EU) 2025/2547 - embedded-emissions methodology
- Implementing Regulation (EU) 2025/2548 - CBAM certificate price
- Implementing Regulation (EU) 2025/2620 - free-allocation adjustment
- Implementing Regulation (EU) 2025/2621 and 2026/1740 - definitive default values
- Implementing Regulation (EU) 2025/2546 and Delegated Regulation (EU) 2025/2551 - verification

## 3. Function-by-function assessment

| Function | Today | 2026 assessment | Gap / action |
|---|---|---|---|
| `normalize_cn` | Normalises CN input to digits | Useful primitive | Retain; add authoritative CN-version validation through TARIC |
| `steel_cbam_scope` | Steel CN scope/exclusions | Useful steel MVP | Replace hard-coded scope over time with versioned Annex I/TARIC dataset |
| `methodology_for` | Selects methodology by production date | Correct architectural pattern | Add effective-to/version supersession tests |
| `source_emissions_tco2` | Measured emissions or activity × EF × oxidation × conversion | Arithmetic core exists | Add unit registry, factor provenance, uncertainty/data-quality controls |
| `calculate_actual_steel` | Direct source emissions, boundary adjustments, precursor emissions, activity-level allocation, audit-only electricity, hashes | Strongest actual-emissions core | Needs stricter production-process/system-boundary semantics and versioned factor provenance; verification is now gated in v2 |
| `persist_calculation` | Persists inputs/result/hash/status | Good audit primitive | Tenant-bind record and immutable supersession/version chain |
| `import_defaults` | Imports versioned Commission defaults | Good fail-closed design | Import official workbook directly and validate schema/hash/signature/provenance |
| `select_default` | Country/CN/route selection; fallback to Other countries; applies 10/20/30% steel markup | Aligned with 2025/2621 default-value structure | Route must come from authoritative dataset, not caller guess; regression-test official India steel rows |
| `import_benchmarks` | Imports benchmark data | Correct data-driven design | Direct official workbook parser + schema/version validation |
| `select_benchmark` | CN/route benchmark selection | Useful | Tighten 4/6/8-digit matching rules and production-route semantics against official tables |
| `import_cscf` / `_cscf` | Versioned CSCF table | Good | Verify official source version in scheduled source pipeline |
| `free_allocation_adjustment` | CBAM factor × CSCF × benchmark × mass | Core FAA implemented | Add official-table golden tests for representative steel routes |
| `certificate_obligation` **NEW** | Embedded tCO2e − FAA − legally pre-converted carbon-price reduction | Fills major commercial/calculation gap | Feed official quarterly 2026 certificate price automatically |
| `calculate` v2 | Actual/default + FAA + blockers | Now produces certificate obligation and declaration-readiness gate | Still needs annual aggregation/declaration pack and Registry XML |
| `validate_verification_report` | Required installation/verifier/monitoring-plan/assurance fields | Good schema gate | Validate against official report/template schema, accreditation source and signed report |
| `build_pack` | Monitoring plan + operator report + verification report readiness | Strong evidence gate | Cryptographic evidence manifest and immutable revision chain |
| `market_access_compiler_v2.compile_shipment` | Combines customs, PPWR, REACH/SCIP, sanctions, valuation, origin and evidence | Strategic differentiator | Integrate CBAM v2 result directly as a first-class engine |
| `/api/cbam/v2/calculate` | Exposes definitive calculator | Correct API surface | Auth/tenant-bind for production; persist v2 calculation and source versions |
| `/api/cbam/verification/pack` | Verification readiness | Valuable | Link pack IDs/hashes into passport |
| `/api/market-access/v2/compile` | READY/BLOCKED decision | Product-level wedge | Return passport ID, reused evidence and € revenue-at-risk |

## 4. Missing 2026 capabilities - prioritized implementation backlog

### P0 - required before claiming a production CBAM engine
1. **Official reference-data ingestion.** Parse Commission default/benchmark workbooks directly; store URL, CELEX, publication/effective date, SHA-256 and parser version.
2. **Golden legal fixtures.** At least 20 representative steel CN/origin/route cases manually reconciled to official tables.
3. **Actual-emissions system-boundary validation.** Encode production process, source stream, precursor and allocation constraints from 2025/2547 instead of accepting arbitrary arithmetic inputs.
4. **Verification binding.** A calculation using actual emissions is not declaration-ready unless bound to a valid verification pack/report. This branch adds the first fail-closed gate.
5. **Certificate obligation.** This branch adds gross embedded emissions, FAA deduction, net certificate-equivalent obligation and optional cost from an official/supplied certificate price.
6. **Carbon-price-paid deduction.** Do not infer this from a raw INR/EUR value. Store the underlying payment/rebate evidence and apply a reduction only through the legally applicable conversion methodology. This branch therefore accepts only an already legally converted certificate reduction.
7. **Annual declarant aggregation.** Aggregate imports by reporting year/goods/origin/installation with retained calculation and verification provenance.
8. **Declaration output.** Generate and validate the applicable CBAM Registry exchange format when its definitive schema is pinned and tested.

### P1 - pilot-grade
9. Official certificate-price snapshot ingestion and versioning.
10. 50-tonne de-minimis/authorisation screening with electricity/hydrogen exceptions handled separately.
11. Data-quality scoring and uncertainty flags.
12. Amendment/supersession workflow when supplier or verifier data changes.
13. Tenant-scoped immutable audit history.
14. Postgres production integration tests.

### P2 - scale
15. Extend beyond steel to aluminium, cement, fertilisers, hydrogen and electricity.
16. Scenario engine: actual vs default, supplier A/B, production-route and price sensitivity.
17. Portfolio certificate forecasting and cash planning.
18. Registry submission workflow/approval controls where legally and technically supportable.

## 5. Reusable EU Market-Access Evidence Passport

### Product definition

A passport is a **versioned, permissioned evidence graph**, not a PDF. It should let an exporter verify an installation/product fact once and reuse it across eligible buyers, shipments and regulations without silently reusing stale or inapplicable evidence.

```
Organisation / Facility
        |
        +-- Installation identity + operator
        +-- Monitoring plan
        +-- Verifier / accreditation
        +-- Production routes
        |
      Product
        +-- CN / TARIC classification
        +-- composition / BOM
        +-- origin facts
        +-- PCF / embedded emissions
        +-- precursor chain
        |
     Evidence objects
        +-- issuer
        +-- validity
        +-- jurisdiction
        +-- scope
        +-- source hash
        +-- verifier state
        +-- permissions
        |
      Shipment / Order
        |
        +-- CBAM
        +-- TARIC/customs
        +-- origin
        +-- steel trade measures
        +-- REACH/SCIP
        +-- PPWR
        +-- DPP
        |
   READY / CONDITIONAL / BLOCKED
```

### Passport data model

**Passport**
- passport_id, tenant_id, subject_type, subject_id, version, status
- valid_from, valid_until, supersedes, created_at
- policy/evidence snapshot hashes

**Evidence object**
- evidence_id, type, issuer, owner, source URI
- SHA-256/content-addressed object reference
- valid_from/to
- jurisdiction
- facility/product/CN/route scope
- verification state and verifier reference
- confidentiality classification
- allowed purposes / recipients

**Claim**
- claim_id, predicate, value, unit
- legal/rule version
- evidence IDs
- calculation ID
- confidence/data-quality
- effective period

**Usage binding**
- shipment/order/buyer
- regulation + obligation
- applicability result
- evidence reused vs newly requested
- decision and timestamp

## 6. Evidence Passport implementation plan

### Phase 1 - 2 weeks: canonical passport
- Add `passports`, `passport_claims`, `passport_evidence_bindings`, `evidence_permissions`.
- Generate facility and product passports from existing supplier/evidence/canonical tables.
- Every evidence object gets hash, issuer, validity, scope and status.
- API: `POST /api/passports`, `GET /api/passports/{id}`, `POST /api/passports/{id}/compile`.
- Compiler refuses stale, wrong-CN, wrong-facility or wrong-purpose evidence.

**Acceptance:** same verified installation evidence can satisfy two eligible shipments without file re-upload, while a scope mismatch fails closed.

### Phase 2 - 2 weeks: CBAM passport
- Bind monitoring plan, installation, production route, precursor data, actual/default calculation, verifier report and certificate obligation.
- Recompile affected shipments whenever an evidence/calculation version changes.
- Generate buyer-facing CBAM evidence bundle with selective disclosure.

**Acceptance:** change one verified installation intensity and show every affected shipment/order and changed certificate exposure.

### Phase 3 - 2-3 weeks: cross-regulation passport
- Bind TARIC document codes, origin proofs, REACH/SCIP, sanctions, PPWR and DPP claims.
- Add rule-specific applicability predicates.
- Add `evidence reuse reason`: SAME_FACILITY, SAME_PRODUCT, SAME_PERIOD, SAME_SUPPLIER, etc.

**Acceptance:** one shipment compiles across CBAM + customs + origin + product-compliance gates from one evidence graph.

### Phase 4 - 2 weeks: external sharing
- Buyer/verifier share links with expiry and purpose limitation.
- Evidence redaction/selective disclosure.
- Downloadable signed manifest: evidence IDs + hashes + versions, not necessarily confidential source files.
- Access log.

**Acceptance:** exporter can share a buyer-specific passport without exposing unrelated customer/commercial information.

## 7. Feature sheet - advantage and competitive pressure

Legend: **Core advantage** = where EuroSetu should differentiate; **Parity** = needed because competitors already do it.

| Feature | Priority | EuroSetu advantage | Competitive pressure / comparable capability | Position |
|---|---:|---|---|---|
| 2026 actual embedded-emissions calculation | P0 | Calculation tied to shipment + market-access decision | CarbonChain, osapiens, SAP publicly describe CBAM calculation | Parity |
| Official default-value calculation | P0 | Fail-closed, versioned regulatory data | Common in mature CBAM tools | Parity |
| Free-allocation adjustment | P0 | Explainable certificate bridge | SAP/osapiens describe certificate requirements/cost | Parity+ |
| Certificate obligation + € exposure | P0 | Put cost against individual order/revenue | osapiens and SAP explicitly advertise cost exposure | Parity |
| Verification evidence pack | P0 | Calculation → verifier evidence → shipment blocker | CarbonChain/osapiens emphasize audit-ready evidence | Parity+ |
| Supplier evidence collection | P0 | Reuse beyond CBAM | CarbonChain and osapiens have supplier portals/workflows | Parity |
| EU Registry XML/export | P1 | One output of broader market-access graph | osapiens and CarbonChain publicly offer XML/report exports | Parity |
| SAP/MES/EMS integration | P0 | Installation/production evidence, not just import rows | SAP naturally owns ERP integration; CarbonChain supports ERP/API import | Must win in industrial depth |
| **Reusable evidence passport** | **P0** | Verify once; permission-share across buyers, shipments and regulations | osapiens publicly promotes shared data foundation/reuse; therefore passport must be more granular and evidence-scoped | **Core advantage if executed deeply** |
| Evidence applicability engine | P0 | Proves *why* evidence may be reused for this CN/facility/period/rule | Less visible as a standalone capability in reviewed CBAM products | Core advantage |
| Evidence hash/provenance/version | P0 | Defensible chain from source → calculation → decision | osapiens advertises source/version/revision audit trail | Parity+ |
| Cross-regulation shipment compiler | P0 | CBAM + TARIC + origin + quota + sanctions + product rules in one READY/BLOCKED decision | osapiens spans many regulations but its CBAM proposition is primarily compliance/carbon workflow | **Core advantage** |
| € order/revenue-at-risk | P0 | Commercial prioritisation, not compliance queue only | CBAM tools emphasize certificate cost; less emphasis on whole-order market-access blockage | **Core advantage** |
| Blocker → owner → remediation | P0 | Operational workflow before shipment | Supplier workflows exist elsewhere; cross-regulation remediation is differentiator | Core advantage |
| India→EU exporter-first workflow | P0 | Producer/exporter evidence reused across many EU buyers | CarbonChain supports manufacturers; most CBAM declarant tooling remains importer-led | Focused wedge |
| Steel quota / trade measures | P0 | CBAM and trade defence interact at same shipment | Not a core public CBAM feature of reviewed carbon tools | **Core advantage** |
| Origin/FTA lifecycle | P1 | Avoid treating negotiated preference as effective | Not central to CBAM-specialist products | **Core advantage** |
| DPP generation from same facts | P1 | Product passport shares evidence graph | osapiens has DPP/product-compliance products | Competitive but valuable |
| Buyer portal/selective disclosure | P1 | Exporter controls reusable evidence | Supplier portals common; purpose-limited cross-regulation sharing is differentiator | Core advantage |
| Regulatory change impact | P1 | Source hash change → affected shipment/passport → recompile | Broad compliance platforms have regulatory update capabilities | Must execute well |
| Multi-CBAM-sector support | P2 | Larger TAM | osapiens supports all six sectors; CarbonChain broader commodities | Parity later |

## 8. Competitor map

### osapiens
Public positioning is the closest strategic warning. It already markets a shared data foundation, supplier data collection, embedded-emissions calculation, expected certificate costs, XML exports, DPP/product compliance and reuse of master data across compliance suites. EuroSetu therefore **cannot claim “reuse data across regulations” alone as a moat**. The differentiator must be transaction-level market-access compilation, exporter-side evidence portability, trade/customs measures and explainable READY/BLOCKED decisions.

Source: https://osapiens.com/en/solutions/carbon-management/cbam

### CarbonChain
Strong in commodity/manufacturer carbon data, supplier engagement, CBAM calculations, audit-ready reports, XML and cost modelling. EuroSetu should not compete on carbon-factor breadth initially. Differentiate on legal/trade applicability and evidence-to-shipment orchestration.

Source: https://www.carbonchain.com/cbam/signup

### SAP
In 2026 SAP announced an end-to-end declarant solution based on Sustainability Footprint Management and Green Ledger, combining customs/ERP/supplier data and calculating embedded emissions, certificate requirements and estimated costs. EuroSetu should treat SAP as a **data source and integration surface**, not attempt to replace ERP.

Source: https://news.sap.com/2026/06/sap-introduces-cbam-declarants-solution/

### Dubrink
CBAM-focused technology/advisory with forecasting, reporting and supply-chain automation, plus PPWR. Competing head-on as another CBAM portal is unattractive.

Source: https://www.dubrink.com/

## 9. Recommended product boundary

Do **not** position:
> EuroSetu is a better CBAM calculator.

Position:
> EuroSetu compiles an industrial order against the evidence and regulatory conditions required for EU market access. It calculates CBAM, but CBAM is one executable rule family in the shipment decision.

The defensible loop is:

```
ERP/MES/EMS + supplier evidence
        ↓
Reusable Market-Access Evidence Passport
        ↓
Versioned regulatory engines
        ↓
Shipment/order compiler
        ↓
READY / CONDITIONAL / BLOCKED
        ↓
€ revenue at risk + exact remediation
        ↓
Evidence update
        ↓
automatic recompile
```

## 10. Next engineering sequence

**Sprint A:** official CBAM datasets + golden steel fixtures + certificate-price snapshots.  
**Sprint B:** passport schema/API + scope-aware evidence reuse.  
**Sprint C:** bind CBAM calculation/verification to passport and market-access compiler.  
**Sprint D:** buyer/verifier selective sharing + immutable manifest.  
**Sprint E:** SAP/MES pilot on 10-25 real anonymised shipments.

### Pilot success metrics
- ≥95% of shipment requirements trace to a rule/source version.
- 100% of CBAM actual-emissions decisions trace to calculation + verification evidence.
- ≥60% evidence reuse across repeat shipments from same installation/product during valid period.
- <5 minutes to recompile an order after evidence changes.
- Every BLOCKED order exposes owner, missing evidence, legal/rule basis and € value at risk.
- Zero silent use of stale/default/regulatory data.
