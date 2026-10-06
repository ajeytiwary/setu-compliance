# Public/app split release record — 2026-10-06

## Shipped and verified

- Merged upstream regulatory snapshot commit `ad4427a` with local dossier commit `bd28a9e` without tracked-file conflicts. `third_party/PaddleOCR` remained untracked and untouched.
- Public allowlist build: `python3 scripts/build_public_site.py dist/public`. It emits marketing, guide, legal, calculator, template, and immutable benchmark files; no customer PDFs, SQLite database, or app-only JavaScript.
- Cloudflare Pages project `eurosetu-public` is Git-connected to `ajeytiwary/setu-compliance`. Production auto-deployment is disabled until the app-host gates pass. A verified preview is at `https://public-split-preview.eurosetu-public.pages.dev`.
- Mobile browser sweep on the Pages preview returned 200 for `/`, `/product`, `/guides`, `/demo`, `/case-study`, and `/benchmarks`; no page errors or horizontal overflow. Benchmarks rendered release `2a7a0ab65b1e`, 52/52 cases.
- App split-host middleware is opt-in (`EUROSETU_SPLIT_HOSTS=1`), rejects wrong hosts, excludes marketing routes, protects public proxy endpoints with `EUROSETU_PUBLIC_PROXY_SECRET`, and keeps admin APIs bearer-gated. Production `/demo`, `/case-study-run`, and `/pilot` redirect to the tenant-scoped real dossier workflow; the blocked legacy `/v1` case-study API remains unavailable.
- Targeted Python tests: 20 passed, 2 skipped for ingestion/evidence/release/storage; 13 passed for TARIC/CBAM/time-travel/public split. Pages Function Bun tests: 3 passed.
- An isolated production-config FastAPI instance with a temporary SQLite database passed a Chromium host-routing sweep. A two-PDF upload produced 2 graph nodes, 1 candidate link, 1 source-value conflict, and BLOCKED. A separate verifier approved the invoice; the dossier stayed BLOCKED, as required by remaining gaps. The running client container was not touched.

## Open release gates

1. The Git-sourced Pages build `9d53ef1e-9448-44bf-a780-c30d0feddae2` cloned commit `fe4f000` and completed successfully after a long build stage. It was triggered through the Pages API. Git pushes to both `public-split-preview` and `public-split-validation` created no deployment, so automatic push-to-deploy remains **unproven**; verify the Cloudflare GitHub App/webhook installation before enabling production auto-deployment.
2. `app.eurosetu.trade` is not yet published. The active tunnel ingress serves only `eurosetu.trade` and `www.eurosetu.trade`. The running `eurosetu` container is an older image and lacks `EUROSETU_ENV`, split-host settings, and the public proxy secret.
3. The current app volume contains 12 lead records. An approved private backup destination and tested restore are required before replacing the container or migrating its database. The old app and root-domain DNS remain unchanged.
4. A Pages `PUBLIC_PROXY_SECRET` and matching app secret, plus Cloudflare WAF rate rules for public form/calculator routes, must be configured before the public domain moves. Contact persistence and notification through the Pages proxy have not yet been live-tested.
5. A dedicated tenant-scoped pilot dashboard is still absent; `/pilot` routes to the dossier UI because its legacy dashboard APIs remain blocked in production. The authenticated upload → evidence review → release packet → reviewer decision browser journey must be repeated on the new app host before cutover. The live production domain still has the old page/route 404s until DNS changes.

## Cutover and rollback

After the gates pass, publish `app.eurosetu.trade` to the tunnel and deploy the new app against backed-up persistent storage; verify health, auth, dossier flow, proxy secret, and admin queue. Then enable Pages production deployment for `main`, verify its pages.dev URL, attach `eurosetu.trade`, and switch the root hostname. Retain the existing app image, volume snapshot, tunnel configuration, and DNS record for immediate rollback. Monitor public 404s, form failures, app auth failures, and dossier API errors.
