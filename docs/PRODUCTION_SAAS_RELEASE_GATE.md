# Production SaaS release gate

The recurring operational subscription is **closed**. The `/pricing` page offers only a scoped, human-reviewed diagnostic or design-partner pilot until every item below is evidenced.

## Deployment implemented now

`docker-compose.production.yml` runs a single-tenant application instance. It uses the application's actual SQLite database at `/app/data/eurosetu.db` on the `eurosetu_data` named volume. The previous Compose file provisioned Postgres while the application still wrote SQLite to unmounted container storage. `DATABASE_URL` is now rejected on production startup to prevent that false persistence assumption. `EUROSETU_DEPLOYMENT_TENANT` is required, and authenticated dossier requests for any other tenant are denied. Legacy `/api`, `/v1`, and `/internal` operational routes without complete tenant scoping are unavailable in production. `/health/ready` checks the operational database and, when recurring SaaS is enabled, reevaluates the commercial gate. The Compose deployment passes through `EUROSETU_BACKUP_BUCKET` and keeps `EUROSETU_RECURRING_SAAS_ENABLED=0` by default.

This is an isolated-instance pilot architecture, **not** a shared-database multi-tenant architecture. One customer requires one separately configured app and volume. Do not put two customer tenants in one instance. The public demo and existing unscoped APIs remain available in development only.

## Backup and restore

Use the SQLite online-backup API, not a live file copy. Run from a container or host with access to the persistent database and a separate backup destination:

```sh
python scripts/sqlite_backup.py backup /app/data/eurosetu.db /backups/tenant-a-2026-10-05.db --tenant tenant-a
```

The command writes a consistent database snapshot plus a JSON manifest with tenant ID, size and SHA-256, and checks SQLite integrity, required tables, single-tenant ownership, foreign-key integrity for linked client documents and events, and absence of legacy unscoped operational rows. It refuses to label a mixed or other-tenant database as this tenant, and restore repeats the ownership check. Copy both files to separately controlled, encrypted storage with a documented retention policy. An explicit S3-compatible upload/read-back/restore drill is implemented in `scripts/run_recovery_drill.py`, requesting server-side AES-256 encryption. Automatic scheduling, a trusted bucket, bucket retention/immutability, and a production drill are **not yet configured**. Until an approved scheduler and destination exist, a daily manual drill is necessary to keep a paid instance healthy; the gate will otherwise close after 26 hours. The recovery command must be run only for a tenant-approved private destination.

For recovery, stop the app, restore into a **new** path, verify it, and only then arrange the volume swap:

```sh
python scripts/sqlite_backup.py restore /backups/tenant-a-2026-10-05.db /recovery/eurosetu.db --tenant tenant-a
```

Restore refuses a tenant mismatch, altered backup, or existing destination. The automated test restores dossier metadata and stored document bytes. A production restore drill with a real deployment and measured RPO/RTO is still required.

## Evidence and commercial acceptance still required

1. Obtain a consented, genuine, same-shipment India-to-EU steel dossier with invoice, packing list, shipping bill, B/L, MTC, actual import declaration, installation emissions communication and verification evidence. Public examples currently span different shipments or are historical/educational.
2. Label critical fields and table rows independently, including source page and bounding box or workbook cell. Measure extraction precision, recall, row association, processing time and human correction time on real client documents.
3. The real-dossier API now accepts source-cited release packets, checks required document roles, quoted PDF page/box or workbook cell facts, cross-document links, Indian origin, EU destination, CN, weight/value/currency and a deterministic mass × verified SEE calculation plus versioned benchmark/CSCF free-allocation and certificate estimate. A separate reviewer can approve or reject with a reason; hashes and an append-only event record bind the decision, and later source changes revoke READY. The synthetic policy test reaches READY, but **no genuine same-shipment dossier has passed this path**. Reviewer field correction UX, independent authenticity checks and authority acceptance of the estimated CBAM obligation remain outstanding.
4. Configure a private off-host backup destination and run a real restore drill. The `EUROSETU_RECURRING_SAAS_ENABLED=1` startup switch refuses activation until there is a reviewer-approved READY dossier, a separate customer-origin signoff backed by a consent PDF and independent admin approval, valid single-tenant storage, a configured bucket, and a recorded off-host restore drill completed after the signoff and within the last 26 hours. Runtime readiness returns 503 when this evidence becomes stale or invalid, and paid-mode dossier writes also return 503 until the gate is repaired. Read-only dossier inspection and the admin readiness report remain available. The runtime check revalidates approved customer-signoff candidates and their current evidence, so it does not reread every historical dossier on each write; the admin report performs the broader audit. Docker Compose marks the container unhealthy; a production traffic router must also remove unhealthy instances, because Compose health status alone does not stop direct requests to port 8000. The backup destination and automatic upload have not been authorised or configured. Per-subject production bearer-token revocation is implemented at `POST /api/admin/revoke-principal` and enforced on every authenticated request; an administrator must record a reason. During any database restore, reapply revocations made after the backup before opening access, because the restored snapshot can predate them. Deletion/retention, monitoring, retry behavior, incident response and customer acceptance still need proof before changing the public subscription offer.

A synthetic READY dossier is a demonstration, not evidence for item 3. The new signoff is a human customer and admin assertion bound to the dossier fingerprint and consent PDF hash; software cannot establish that a signatory or shipment is genuine without independent identity and source checks. The signed consent PDF must be inspected before approval. Tests simulate this protocol with synthetic files and do not supply commercial evidence. The present tests prove the prototype boundary and local recovery behavior; they do not prove commercial release.

## Explicit off-host recovery command

With a tenant-approved private S3 bucket and credentials configured, run:

```sh
EUROSETU_ENV=production EUROSETU_DEPLOYMENT_TENANT=tenant-a \
EUROSETU_DB_PATH=/app/data/eurosetu.db EUROSETU_BACKUP_BUCKET=approved-private-bucket \
python scripts/run_recovery_drill.py
```

The command backs up SQLite consistently, uploads the database and manifest requesting AES-256 server-side encryption, downloads both, restores into a new temporary database, verifies hashes and row counts, then records the completed drill. It does not configure a schedule or bucket policy. Test credentials and retention separately before using client documents.
