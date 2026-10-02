# Deploy EuroSetu on Google Cloud (Cloud Run)

Fully managed option: Google runs the container, autoscales it (including to
zero when idle), terminates TLS, and gives you a public `https://…run.app`
URL. Same Docker image as everywhere else - no code changes.

**Cost sketch:** Cloud Run's free tier usually covers a pilot site; beyond
that you pay per request/vCPU-second. A Cloud SQL database is the main
optional cost (see §4).

**Prerequisites:** a Google Cloud project with billing enabled,
`gcloud` CLI installed and logged in (`gcloud auth login`).

```bash
export PROJECT=your-gcp-project
export REGION=asia-south1   # Mumbai; use europe-west1 for EU data residency
gcloud config set project "$PROJECT"
gcloud services enable run.googleapis.com artifactregistry.googleapis.com \
  cloudbuild.googleapis.com secretmanager.googleapis.com
```

---

## 1. Build the image in the cloud

```bash
gcloud artifacts repositories create eurosetu --repository-format=docker \
  --location="$REGION" --description="EuroSetu images" || true

gcloud builds submit --tag "$REGION-docker.pkg.dev/$PROJECT/eurosetu/app:latest" .
```

## 2. Deploy to Cloud Run

The image honours the `PORT` variable Cloud Run injects, and serves on
`0.0.0.0` with `--proxy-headers`, so HTTPS and client IPs work as-is:

```bash
gcloud run deploy eurosetu \
  --image "$REGION-docker.pkg.dev/$PROJECT/eurosetu/app:latest" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --port 8000 \
  --memory 1Gi --cpu 1 \
  --min-instances 0 --max-instances 5 \
  --set-env-vars EUROSETU_DB_PATH=/tmp/eurosetu.db
```

Cloud Run prints a public URL like
`https://eurosetu-abc123-uc.a.run.app`. Open it: `/`, `/trust`,
`/case-study`, `/demo` should all respond.

> **SQLite caveat:** Cloud Run's filesystem is ephemeral - `/tmp/eurosetu.db`
> resets on each cold start. That is fine for the marketing site and demo,
> but **contact submissions and demo leads will not persist**. For a pilot
> that must keep them, do §4 (Cloud SQL + Postgres) instead of `/tmp`.

## 3. Custom domain (optional)

```bash
# Verify the domain in Search Console first, then:
gcloud run domain-mappings create --service eurosetu \
  --domain eurosetu.example.com --region "$REGION"
```

Add the DNS records Cloud Run shows you, and HTTPS is provisioned
automatically.

## 4. Persistent database (recommended for real pilots)

The app ships with SQLAlchemy + `psycopg` in `requirements.txt` and a
`app/production_db.py` helper for exactly this move. Typical setup:

1. Create a small Postgres instance:
   ```bash
   gcloud sql instances create eurosetu-db --database-version POSTGRES_16 \
     --tier db-f1-micro --region "$REGION" --storage-size 10GB
   gcloud sql databases create eurosetu --instance eurosetu-db
   gcloud sql users create eurosetu --instance eurosetu-db \
     --password "$(gcloud secrets create db-password --replication-policy=automatic \
       --data-file=<(openssl rand -base64 24) >/dev/null; gcloud secrets versions access latest --secret=db-password)"
   ```
2. Put the connection string in Secret Manager as `DATABASE_URL`
   (`postgresql+psycopg://eurosetu:<password>@/<db>?host=/cloudsql/PROJECT:REGION:eurosetu-db`).
3. Redeploy with the Cloud SQL connection attached:
   ```bash
   gcloud run deploy eurosetu \
     --image "$REGION-docker.pkg.dev/$PROJECT/eurosetu/app:latest" \
     --region "$REGION" \
     --add-cloudsql-instances "$PROJECT:$REGION:eurosetu-db" \
     --update-secrets DATABASE_URL=db-connection:latest \
     --set-env-vars EUROSETU_DB_PATH=/tmp/eurosetu.db
   ```
   Wire `DATABASE_URL` through `app/production_db.py` at startup
   (see `docs/SOURCE_SYNC.md` for the sync-service pattern), then run
   `migrations/001_production_tenancy.sql` once against the new database.

## 5. Updates and rollback

```bash
# New version
gcloud builds submit --tag "$REGION-docker.pkg.dev/$PROJECT/eurosetu/app:v2" .
gcloud run deploy eurosetu --image "$REGION-docker.pkg.dev/$PROJECT/eurosetu/app:v2" --region "$REGION"

# Roll back to the previous revision
gcloud run revisions list --service eurosetu --region "$REGION"
gcloud run services update-traffic eurosetu --region "$REGION" --to-revisions <PREV>=100
```

## 6. Operations checklist

- **Logs:** `gcloud run logs read eurosetu --region "$REGION"` (or Cloud Logging console).
- **Health:** the image's `HEALTHCHECK` hits `/robots.txt`; Cloud Run's own
  startup probe uses the same port contract.
- **Secrets:** never bake credentials into the image - use
  `--update-secrets` / Secret Manager. `.dockerignore` already keeps
  `.env` and local `*.db` files out of builds.
- **EU data residency:** choose `europe-west1` (Belgium) or `europe-west3`
  (Frankfurt) as `$REGION` if customer data must stay in the EU.
