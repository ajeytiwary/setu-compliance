# EuroSetu Compliance - CI, Platform and Client-Facing Website Review
**Review date:** 30 September 2026  
**Repository:** ajeytiwary/setu-compliance  
**Branch reviewed:** main  
**Review branch:** review/platform-client-ci-20260930

## Executive summary

EuroSetu is materially stronger than the earlier generic compliance build. The repository now has a coherent steel/industrial-export wedge, a working public landing page, a lead-gated demo, a pilot operations view, a deterministic regulatory/evidence architecture, and current CI runs that are green.

The latest three CI runs inspected on `main` all passed. The remaining known workflow risk is external-source synchronization: the scheduled "Sync pluggable regulatory sources" previously failed because the EUCDM distribution returned HTTP 403 from a GitHub-hosted runner. That issue was subsequently addressed in source synchronization logic using a fail-closed validated-snapshot fallback. The ordinary CI suite is currently green.

The largest production-readiness gap is no longer basic functionality. It is the boundary between a convincing pilot/demo and a secure multi-tenant production product. The code contains production-readiness primitives (tenant principal, role checks, PostgreSQL tenant context, evidence hashing), but the public/demo application still relies on a lightweight lead token and a substantial amount of synthetic data. That is acceptable for demos if clearly labeled, but it should not be confused with production authentication, authorization, tenant isolation, immutable custody or regulator/verifier acceptance.

## 1. Current CI and workflow status

### Green CI
At the time of review, these recent CI runs on `main` were successful:
- Run 36766659244 - success
- Run 36764157346 - success
- Run 36752580048 - success

The current CI performs:
1. checkout;
2. Python 3.12 setup;
3. dependency installation;
4. full pytest suite, including unit, API and web smoke tests.

This is a useful baseline because the suite includes the public website-to-demo journey and gated API checks.

### Regulatory workflow history
- "Sync EU regulatory data" most recently inspected scheduled run: success.
- "Sync pluggable regulatory sources" most recently inspected scheduled run: failure.
- The failure was isolated to the EUCDM upstream returning HTTP 403 while TARIC, ECHA candidate-list and sanctions data were successfully processed in the same run.

The correct engineering response is not to mark a blocked upstream fetch as fresh. The current synchronization implementation now supports a stale-but-previously-validated fallback marker for EUCDM so that a transport failure does not manufacture new legal/regulatory data.

### CI improvements recommended
**P1**
- Add explicit dependency caching to reduce latency and variance.
- Add a static syntax/import check before the full test suite, e.g. `python -m compileall app tests scripts`.
- Split the test job into:
  - core/unit;
  - API/integration;
  - client/web smoke;
  - production-readiness/security.
  This makes failures much faster to triage.

**P1**
- Add a dedicated scheduled test for source resolvers with mocked upstream failures, so HTTP 403/404/429 behavior is regression-tested without depending on a live publisher.
- Persist a compact source-sync report artifact even when the workflow fails, so failures are diagnosable without reading very large logs.

**P2**
- Upgrade `actions/checkout@v4` and `actions/setup-python@v5` when stable Node-24-native major versions are available. Current runners emit Node 20 deprecation warnings for these actions.

## 2. Platform architecture review

### What is strong
The architecture has a clear product thesis:

`shipment/order -> product/CN/origin -> genealogy/activity/supplier evidence -> regulatory compiler -> readiness/blockers -> remediation -> output pack`

The repository includes dedicated modules for:
- CBAM calculation and verification;
- TARIC and customs;
- steel trade measures;
- origin/FTA;
- REACH/SCIP;
- sanctions;
- supplier remediation;
- evidence graph/store;
- source synchronization and provenance;
- market-access compilation;
- pilot workflow and readiness.

That separation is appropriate for a rules-first assurance product because it prevents a generic AI layer from becoming the source of legal truth.

### Evidence/provenance model
The use of:
- source manifests;
- SHA-256 hashes;
- versioned normalized snapshots;
- explicit legal-authority flags;
- readiness/blocker states;
- evidence custody semantics

is directionally correct and commercially differentiating.

The product should continue to make a strict distinction between:
1. official source;
2. legal authority;
3. validated mirror;
4. synthetic operational data;
5. customer-authorised evidence.

These distinctions are already visible in the repository and should remain visible in every export/dossier.

### High-risk gaps before production

**P0 - Production identity and tenant enforcement**
`app/security.py` accepts identity, tenant and role information from headers. This is suitable as an internal abstraction but not as an authentication mechanism. A production deployment needs an upstream trusted identity provider or signed token validation. Untrusted clients must never be allowed to assert their own `x-eurosetu-subject`, `x-eurosetu-tenant` or role headers.

Recommended minimum:
- OIDC/OAuth identity provider;
- server-side JWT verification;
- tenant membership derived from the database, not request headers;
- role resolution server-side;
- route-level authorization tests for cross-tenant reads/writes.

**P0 - Multi-tenant database proof**
`production_db.py` sets a PostgreSQL tenant context, but production safety requires proving that every tenant-owned table is protected by row-level security or an equivalent repository/service-layer invariant.

Add a cross-tenant regression suite:
- tenant A cannot read tenant B shipments;
- tenant A cannot enumerate tenant B IDs;
- tenant A cannot mutate tenant B evidence;
- export endpoints respect tenant scope;
- background jobs preserve tenant context.

**P0 - Public/pilot mutation boundaries**
The demo and pilot include remediation and evidence actions. Confirm that public lead-gated users cannot access pilot-only mutation endpoints or privileged state merely by discovering the endpoint.

### Medium-priority platform gaps

**P1 - Idempotency and concurrency**
Evidence requests, imports and regulatory snapshot publication should have explicit idempotency semantics. Duplicate browser submits, retrying workers and scheduled jobs should not create duplicate records or conflicting state.

**P1 - Observability**
Add structured logging for:
- correlation/request ID;
- tenant ID;
- source dataset/version;
- shipment ID;
- rule/requirement code;
- decision transition;
- evidence hash;
- actor.

Never log sensitive source payloads or credentials.

**P1 - Regulatory change impact**
The source-sync architecture should trigger deterministic impact analysis:
`new source hash -> affected rule pack -> affected shipments -> changed readiness -> review queue`.
This should become a first-class product feature rather than only an ingestion concern.

## 3. Client-facing website review

### Positioning
The current homepage has a much clearer proposition than a general compliance site:

> Know whether an export order can enter its market before it becomes a shipment problem.

That is strong because it sells an operational/commercial outcome rather than regulation itself.

The three-step framing - Compile obligations, Trace evidence, Prioritise by money - is also good. It aligns compliance activity to revenue-at-risk, which is likely to resonate with export/commercial leadership more strongly than a generic GRC message.

### Strong elements
- Clear India -> EU first wedge.
- Explicit focus on steel, metals and engineering.
- The synthetic-shipment disclaimer is present.
- Pricing and pilot scopes are visible.
- Engineering assurance / not legal certification language is visible.
- "Not another CBAM calculator" differentiation is useful.
- The site speaks to a bounded pilot rather than an enterprise transformation.

### Client-conversion issues

**P0 - The primary CTA currently terminates at GitHub**
The "Bring one real EU-bound shipment" section ends with "View EuroSetu on GitHub" and says the commercial contact channel is still being finalised.

For a client-facing site, this is the biggest conversion leak. A commercial buyer should be able to:
- request a diagnostic;
- book a call;
- submit a work email and company;
- optionally provide CN code / export corridor / annual EU export value.

GitHub should be a trust/transparency secondary link, not the principal sales action.

**P1 - Primary navigation is too broad for conversion**
The top navigation exposes Platform, Services, Pricing, Team and Demo. "Team" is less commercially important than:
- Case study;
- Security & trust;
- Regulatory coverage;
- Contact/book pilot.

For early enterprise sales, move hiring/team content off the primary buyer path.

**P1 - Pricing precision may create false certainty**
The current public pricing is highly specific:
- Diagnostic ₹2-3 lakh / €2-3k;
- Pilot ₹6.5-7.5 lakh / €6.5-7.5k;
- Enterprise validation ₹18-25 lakh / €18-25k;
- recurring tiers thereafter.

This can help qualify leads, but the scope varies materially by ERP/MES/EMS access, facility count, supplier count, evidence quality and legal/customs review needs.

Recommended copy:
- keep "starting from" or scoped bands;
- state what drives variation;
- distinguish software/license from implementation/integration services.

**P1 - Missing proof surface**
The website should include one concise, explicitly synthetic/public-data case:
- one HRC shipment;
- one CBAM blocker;
- one quota/current-balance blocker;
- one supplier-evidence blocker;
- amount of order value at risk;
- remediation path;
- final readiness state.

Do not use fabricated customer outcomes. A transparent "worked example" is safer and more credible.

**P1 - Trust and security page**
For customers being asked to provide ERP, MES, EMS, supplier and verifier data, the site needs a trust page covering:
- data residency;
- encryption;
- credential handling;
- tenant isolation;
- retention/deletion;
- subprocessors;
- audit logging;
- backup/restore;
- incident handling;
- production boundary.

Only publish controls that are actually implemented.

## 4. Demo review

### Lead gate
The demo collects:
- full name;
- work email;
- company;
- role;
- problem statement.

That is a sensible sales gate. The public smoke tests verify:
`landing -> demo -> lead creation -> token -> gated dashboard/risk APIs`.

### Security limitation
The demo token should be treated strictly as a marketing/demo-access token, not as a production authorization credential.

Recommended:
- expiry;
- server-side revocation;
- rate limits;
- hashed tokens at rest;
- CSRF/origin strategy for state-changing browser actions;
- separation between marketing demo and pilot/customer authentication.

### Demo copy
"See the control plane on live data" is potentially ambiguous because parts of the experience use synthetic commercial data while regulatory datasets are official/snapshotted.

Change this to:
> See the control plane on live regulatory data and clearly labeled synthetic commercial data.

That is more precise and consistent with the detailed client demo guide.

### Demo UX improvements
- Add a visible "Demo data" provenance badge near KPI values.
- Add empty/error/retry states for each API-backed panel.
- Show source timestamp and hash in the regulatory panel.
- Offer a "Download sample readiness dossier" after the user explores a shipment.
- End the demo with a commercial CTA: "Run this on 10 of your shipments."

## 5. Pilot dashboard review

The pilot dashboard is considerably closer to a client workflow than the public demo. The remediation lifecycle is especially useful:

`filter -> simulate -> request -> verify -> resolve`.

This should become a central product workflow.

### Main issue
The page calls itself:
> INTERNAL + PILOT CUSTOMER

Do not use one authorization boundary for both internal operator functions and customer functions in production.

Create explicit roles/views:
- client viewer;
- client contributor;
- verifier/reviewer;
- EuroSetu operator/admin.

Operations such as marking evidence VERIFIED should require a defined reviewer role and immutable audit entry.

## 6. Regulatory/data-source review

### Positive
The repository correctly refuses to invent missing quota balances or legal states. That fail-closed posture is a core product advantage.

### Source-sync risk
Any mirror should be labeled as a mirror, even when the content has been validated against an official source. The engine should preserve:
- provider;
- authority classification;
- retrieval time;
- source URL;
- payload hash;
- parser version;
- validation result;
- effective/legal date where applicable.

### Recommended freshness model
Each dataset should have:
- expected refresh cadence;
- freshness threshold;
- stale state;
- missing state;
- fallback state;
- legal-impact state.

User-facing decisions should explain whether a blocker comes from:
- missing customer evidence;
- stale regulatory data;
- incomplete source resolution;
- actual negative entitlement.

## 7. Testing review

Current testing coverage includes useful areas:
- market-access pipeline;
- CBAM/FTA;
- regulatory content;
- source synchronization;
- integrations;
- demo lead gate;
- web smoke journey;
- production readiness;
- supplier remediation.

Add the following release-critical tests:

**P0**
1. Cross-tenant authorization matrix.
2. Demo token cannot access pilot/admin routes.
3. Pilot contributor cannot self-verify evidence unless explicitly authorized.
4. Regulatory source stale/fallback status propagates to final entitlement decision.
5. Duplicate evidence/import request is idempotent.

**P1**
6. Browser accessibility tests.
7. Responsive/mobile smoke tests.
8. Broken external source resilience: 403, 404, timeout, invalid MIME type, truncated payload.
9. Hash/source-version change causes impact recalculation.
10. Export/dossier contains all provenance and caveats.

## 8. Recommended product roadmap

### Next 48 hours
- Keep CI green.
- Add source-sync regression tests for upstream 403 and fallback state.
- Replace the homepage GitHub-only pilot CTA with an actual lead/book-call route.
- Clarify demo "live data" wording.
- Add buyer-facing worked example.
- Add explicit role checks around verification/mutation endpoints.

### Next 7 days
- Implement production identity boundary.
- Add cross-tenant tests.
- Add trust/security page.
- Add downloadable sample dossier.
- Add structured application/event logging.
- Build regulatory-change impact queue.

### Next 30 days
- Run 3-5 design-partner workflows on customer-authorised exports.
- Measure:
  - time to map one shipment;
  - evidence-chasing hours avoided;
  - blocker resolution time;
  - revenue value surfaced;
  - percentage of required evidence reusable across shipments.
- Use those observed metrics, not estimates, as the basis of future marketing claims.

## 9. Release gate

Do not call EuroSetu production-ready until all of the following are true:

- [ ] CI green on release commit.
- [ ] Live regulatory integrity workflow green or explicitly degraded with a documented stale/fallback state.
- [ ] Production identity provider configured.
- [ ] Cross-tenant isolation tests pass.
- [ ] Privileged verification actions require explicit roles.
- [ ] Evidence retention/deletion policy implemented.
- [ ] Regulatory provenance visible in exported decisions.
- [ ] Backup/restore tested.
- [ ] Security review completed.
- [ ] Customer pilot boundary and legal/engineering disclaimers approved.
- [ ] No synthetic KPI is presented as a customer outcome.

## Overall assessment

EuroSetu now looks like a credible **pilot-stage market-access operating system** rather than a generic compliance dashboard. The differentiation is strongest where it combines shipment context, regulatory rules, evidence provenance, remediation and commercial value.

The next milestone should not be adding more regulations indiscriminately. It should be proving that the existing steel workflow is secure, tenant-safe, source-current and materially faster for a real exporter than spreadsheets, email and disconnected specialist tools.
