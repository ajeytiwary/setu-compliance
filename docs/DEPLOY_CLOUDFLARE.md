# Deploy EuroSetu's public site and hosted app

The deployment uses two hosts. `eurosetu.trade` serves the public, static marketing site through Cloudflare Pages. `app.eurosetu.trade` serves the interactive FastAPI app through Cloudflare Tunnel. The public build must never include client documents, the application database, bearer tokens, or app-only HTML and JavaScript.

## Prerequisites

- A Cloudflare account with `eurosetu.trade` DNS and Pages access, and a connected hosted Git repository.
- A running FastAPI app at `127.0.0.1:8000`, a persistent private database volume, and a named Cloudflare Tunnel on the app machine.
- A private, approved backup destination with a tested restore procedure before real client records are accepted.
- A public proxy secret shared between Pages Functions and the app; store it as a Cloudflare secret and an app environment variable. Do not commit its value.

## Build and preview the public site

From the repository root:

```bash
.venv/bin/python scripts/build_public_site.py dist/public
```

The build copies an allowlist of public HTML, CSS, JavaScript, and immutable benchmark artifacts. It generates public guides and legal pages. Inspect `dist/public` before uploading; it must contain no client PDFs, SQLite files, app-only pages, or credentials. The public `/demo` and `/case-study` pages are informational. Their interactive counterparts run on the app host.

Connect the repository to Cloudflare Pages. Set the production branch to the reviewed release branch, the build command to `python3 scripts/build_public_site.py dist/public`, and the output directory to `dist/public`. Configure `APP_ORIGIN=https://app.eurosetu.trade` and the secret `PUBLIC_PROXY_SECRET` for the Pages Functions. Pull requests receive Pages preview URLs; run the route and link audit there before merging.

Pages Functions proxy only the explicitly allowed public contact and calculator endpoints. The app must verify `PUBLIC_PROXY_SECRET` on these proxied requests. Apply Cloudflare WAF rate limits to `/api/contact` and `/api/tools/*`. The supplier CSV is static; all customer uploads and dossier APIs remain on the app host.

## Publish the app through Cloudflare Tunnel

Create or reuse a named tunnel with an ingress rule for the app host:

```yaml
ingress:
  - hostname: app.eurosetu.trade
    service: http://127.0.0.1:8000
  - service: http_status:404
```

Route `app.eurosetu.trade` to the tunnel in Cloudflare DNS. Configure the app's production environment, signed bearer-token secret, allowed host, proxy secret, and private database path. Start with `docker-compose.production.yml` and confirm `/health/ready` locally before opening the tunnel. The backend must reject unexpected hosts and keep privileged APIs bearer-gated. Public links from app pages point back to `https://eurosetu.trade`.

The email key worker in `workers/` sends recipients to `https://app.eurosetu.trade/pilot`. Its signing secret must match the app's pilot-key secret. If using the admin queue, open `https://app.eurosetu.trade/admin` with an administrator token; do not expose that page on the public Pages deployment.

## Cutover gates

1. Crawl the Pages preview navigation, footer, sitemap, guides, legal pages, calculator pages, `/demo`, `/case-study`, and `/benchmarks`. Every linked page and benchmark artifact must load. Check the canonical host and contact address.
2. Inspect the complete `dist/public` artifact for client data, secrets, private code, and app-only assets. Treat any unexpected file as a failed build.
3. Submit a test contact request through Pages and verify persistence and delivery. Exercise all public calculators through the Pages Functions, including rejected inputs and upstream failures.
4. Complete an authenticated app journey: secure dossier workflow (also reached from `/pilot`), document upload, evidence review, blocker remediation, decision replay, and audit traceback. Verify that no anonymous visitor can access client data.
5. Only then move the apex/root DNS from the old tunnel to Pages. Preserve the old DNS and deployment settings for rollback. Keep temporary redirects for old `/pilot`, `/admin`, and document-workflow bookmarks. Monitor 404s, form failures, auth failures, and API errors after the switch.

DNS cutover follows the preview and app-host gates; preserve the existing tunnel and prior DNS settings for rollback.

## Rollback and failure response

If public routes fail, restore the prior root DNS target while leaving the app tunnel intact; retain the previous deployment until the incident is closed. If leads fail, stop acknowledging success and inspect Pages Function and app logs using request IDs. If app auth or upload fails, stop new pilot intake, preserve the data volume, and restore the previous app image. If a private file appears in `dist/public`, halt the Pages deployment and rotate any exposed secret.

Do not use the old single-host Tunnel instructions for the root domain. The public site is released through Pages; Tunnel publishes only the hosted app.
