# Hardening implementation - 1 October 2026

This note records the implementation of the P0/P1 actions identified in the 30 September platform review.

## Implemented

1. **Production auth** - privileged pilot APIs now require signed bearer JWTs. Production can validate OIDC-issued RS256/ES256 tokens through `EUROSETU_OIDC_JWKS_URL`, with issuer/audience checks. HS256 remains a configurable local/test baseline. Tenant membership and roles come from signed claims rather than free-form role headers.
2. **Tenant isolation** - `migrations/001_production_tenant_rls.sql` adds tenant IDs and PostgreSQL row-level-security policies to core customer-owned tables. Adversarial API tests reject a valid token attempting to assert a tenant absent from its signed memberships.
3. **Demo vs pilot privilege separation** - a marketing lead token can access the demo but cannot access pilot APIs. Pilot viewer/contributor/verifier/admin roles are separate; verification and resolution require verifier/admin.
4. **Client conversion** - the homepage pilot CTA enters the lead/demo funnel; GitHub is secondary.
5. **Trust layer** - `/trust` documents implemented controls and clearly separates them from deployment requirements/certifications not held.
6. **Regulatory change impact** - successful source hash changes create persistent `REVIEW_REQUIRED` shipment impact rows with mapped rule families. Authenticated users can inspect `GET /api/regulatory/change-impact`. Same-hash syncs are idempotent.
7. **Demo credibility** - `/case-study` provides an explicit synthetic HRC worked example and distinguishes synthetic commercial values from regulatory provenance.
8. **Test expansion** - tests now cover demo→pilot privilege crossing, tenant-membership abuse, viewer mutation denial, tampered JWTs, regulatory impact/idempotency, upstream EUCDM 403 stale fallback, trust/case-study routes and responsive viewport metadata.

## Important deployment boundary

The PostgreSQL RLS migration must be applied before production customer traffic. The SQLite demo database remains a development/demo store and is not evidence of production tenant isolation.

OIDC requires the deployment to configure:
- `EUROSETU_OIDC_JWKS_URL`
- `EUROSETU_JWT_ISSUER`
- `EUROSETU_JWT_AUDIENCE`

The identity provider must issue a signed `tenants` object mapping tenant IDs to roles. In a mature deployment, tenant membership should additionally be reconciled against the application database/identity directory so revocation does not depend solely on token expiry.

## Remaining follow-up

- Add an interactive OIDC login/session flow for the browser pilot UI; the API security boundary is implemented, but deployment UX depends on the selected identity provider.
- Run the PostgreSQL RLS migration against a disposable production-like database and add database-level two-tenant integration tests.
- Add formal accessibility automation (axe/Playwright) when browser CI is introduced; current tests cover route availability and responsive metadata, not WCAG conformance.
- Define dataset-specific impact selectors so a regulatory source update queues only truly affected CN/origin/date combinations rather than conservatively queueing all shipments for the mapped rule family.
