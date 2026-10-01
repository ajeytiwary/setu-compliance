# Pilot key issuance (manual, founder-sent)

Two paths mint the **same** HS256 bearer key (`app/pilot_keys.py` is the
source of truth; the Worker is a WebCrypto port). Both keep the manual step:
**the founder sends the key from Gmail**. Nothing auto-emails the requester.

## Path A — /admin queue (recommended daily driver)

1. Founder mints a personal admin key once:
   `EUROSETU_JWT_SECRET=<prod-secret> python scripts/mint_pilot_token.py --tenant tenant-a --roles admin --days 90`
2. Open `https://eurosetu.trade/admin`, paste the admin key (Unlock).
3. Newest contact enquiries + demo leads appear. Click **Mint key**, copy the
   token, send it manually from Gmail with the tenant name.
4. Requester opens `https://eurosetu.trade/pilot`, pastes the key + tenant.

Endpoints (both require the `admin` role):
- `GET /api/admin/requests` — contacts + leads, newest first (200 max each).
- `POST /api/admin/mint {"email","tenant?","roles?","days?"}` — returns
  `{"email","tenant","roles","days","token"}` and audits `pilot.key_minted`.

## Path B — Email Worker (request@ -> pilot@)

For requesters who email instead of using the site form:

1. `cd workers && npm i -g wrangler && wrangler login`
2. `wrangler secret put EUROSETU_JWT_SECRET` — paste the **same** value the
   app runs with (never commit it).
3. `wrangler deploy` (uses `workers/wrangler.toml`).
4. Cloudflare dashboard → Email → Email Routing → Routing rules:
   - `request@eurosetu.trade` → **Send to Worker** → `eurosetu-pilot-key-minter`
   - `pilot@eurosetu.trade` → **Send to an email** → your Gmail (unchanged)
5. Someone emails `request@eurosetu.trade`. The Worker mints a key and
   forwards the message to `pilot@eurosetu.trade` with headers:
   `X-EuroSetu-Pilot-Key`, `X-EuroSetu-Key-For`, `X-EuroSetu-Tenant`,
   `X-EuroSetu-Roles`, `X-EuroSetu-Days`.
6. Founder opens Gmail → Show original → copies the key → Gmail-sends it to
   the requester manually.

Subject-line overrides (optional): `tenant=acme-corp roles=pilot_viewer
days=14`. Unknown roles are dropped; out-of-range days clamp to 1–365.

> Email Workers **cannot rewrite the forwarded body** — only forward with
> extra headers. That is why Path A (/admin) is the easier copy-paste UI and
> Path B is a convenience for email-first requesters.

## Parity test vector

`app/pilot_keys.mint_pilot_key("s", "tenant-a", ["pilot_viewer"], 30,
"a@b.co", now=1700000000)` must equal the Worker's output for the same
inputs (see `tests/test_pilot_key_issue.py`). If they ever diverge, fix the
Worker — `app/security.py` only accepts the Python shape.
