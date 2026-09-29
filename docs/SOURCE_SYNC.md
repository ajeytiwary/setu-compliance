# Source Sync — Auto + Weekly + Manual Refresh

Upstream EU reference data is **materialized**, not stubbed. Two complementary
pipelines share one CLI (`scripts/sync_sources.py`), both fail-closed, both
write hashed versioned snapshots, and engines consume **normalized only**.

## Auto (CI-safe, link-discovery) — 5 pluggable sources

```bash
python scripts/sync_sources.py                       # 5 auto sources (positional default)
python scripts/sync_sources.py taric_measures eucdm  # subset
python scripts/sync_sources.py --strict              # CI: exit 1 if any source fails
```

Resolvers live in `app/source_sync.py` (`discover()` scrapes official landing
pages for versioned distributions: ECHA CSV, SCIP 6.10 ZIP, FSF 1.1 XML/CSV via
data.europa.eu DCAT, EUCDM ZIP, TARIC via `SETU_TARIC_BULK_URL` or ZIP
discovery). Layout: `data/raw/<ds>/<sha>/` + `data/normalized/<ds>/<sha>/records.json`
+ `data/manifests/<ds>/<sha>.json` + `latest.json` pointer. The GitHub workflow
`.github/workflows/sync-regulatory-sources.yml` runs this daily (04:17 UTC) and
commits validated snapshots. CI (`.github/workflows/ci.yml`) enforces populated
live snapshots via `scripts/sync_live_sources.py` probes.

## Weekly + Manual (versioned) — all 11 registry datasets

Every dataset lands in `data/raw/<dataset>/<YYYY-MM-DD>-<sha8>/`, normalizes into
`data/normalized/<dataset>/<version>/normalized.json`, and gets a manifest with
`dataset_id, provider_id, source_url, retrieved_at, effective_from/effective_to,
SHA256, content_type, record_count, authority, legal_authority, parser_version,
normalizer_version`. Engines consume **normalized only** — never raw Excel/XML.
Raw/normalized/manifests are gitignored (re-downloadable); the checked-in legal
snapshot `data/eu_steel_measure_2026.json` stays authoritative for steel until a
full 26-category 2026/1457 table is imported.

## Weekly (automatic)

```bash
# systemd (server) — Mondays 03:00 UTC, ±30 min jitter
sudo cp deploy/setu-sync.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now setu-sync.timer
systemctl list-timers setu-sync.timer   # verify

# cron fallback (any box)
0 3 * * 1 cd /home/plasmion/git/setu-market-access-mvp-production && PYTHONPATH=. .venv/bin/python scripts/sync_sources.py --all >>/var/log/setu-sync.log 2>&1
```

`--all` syncs every dataset, writes `data/manifests/_sync_report.json`, and
**never stops at the first failure** (exit 1 with per-dataset errors). A dataset
that already has today's manifest is `SKIPPED_FRESH` unless `--force` is passed.
The last good normalized snapshot is never overwritten by a failed fetch
(fail-closed). Sanctions versions are date-foldered and never overwritten, so a
screening can always answer *"what list was in force on 29 Sept?"*.

## Manual (on demand)

```bash
python scripts/sync_sources.py --list                       # where to click per dataset
python scripts/sync_sources.py --dataset eu_sanctions --as-of 2026-09-29
python scripts/sync_sources.py --dataset echa_candidate_list --file ~/downloads/candidate_list_en.csv
python scripts/sync_sources.py --dataset taric_measures --file ./taric-export.csv --as-of 2026-09-29
python scripts/sync_sources.py --all --force                 # re-fetch everything today
```

Some publishers block bots (ECHA returns 403, FSF API needs a bearer token):
the CLI raises a `ValueError` with **download guidance + the `--file`
workaround** instead of silently publishing nothing.

| Dataset | Auto-download | Manual path |
|---|---|---|
| TARIC measures | ❌ (no anonymous bulk file) | Export CSV/XML from TARIC consultation or taric-opendata mirror → `--file` |
| Quota balances | ❌ (consultation export) | Export CSV from QUOTA database → `--file` (daily) |
| EUCDM Annex B / code lists | ❌ | Download .xlsx → `--file` |
| Steel 2026/1457 | ⚠️ EUR-Lex TXT often empty via urllib | Falls back to checked-in legal snapshot; full table via `--file` |
| CBAM defaults / benchmarks | ✅ TAXUD URLs from registry | `--file` if TAXUD rotates UUIDs |
| ECHA Candidate List | ⚠️ 403 to bots | Browser download `candidate_list_en.csv` → `--file` |
| SCIP 6.10 | ❌ | Browser download ZIP → `--file` |
| EU sanctions FSF 1.1 | ⚠️ API needs token | Browser download XML/CSV → `--file` (versioned, never overwritten) |
| Comext India→EU 72/73 | ✅ dissemination API | `--url` override for custom queries |
| UCI steel telemetry | ❌ DEMO_ONLY | Download CSV → `--file` |

## HTTP API (manual refresh from the UI / demo)

```bash
POST /api/data-sources/{dataset}/sync     # {"as_of": "2026-09-29", "url": "...", "force": true}
GET  /api/data-sources/{dataset}/manifest  # latest manifest pointer
GET  /api/data-sources                     # status now includes "manifest" per dataset
```

## Failure semantics (demo-safe)

- Landing pages are **never parsed as truth** — the pipeline raises with a
  `where to click` message instead of inventing rows.
- Empty parses (e.g. landing-page HTML fed as TARIC XML) yield zero records and
  **refuse publication** (`RECORD_COUNT_BELOW_MINIMUM`).
- Steel annex with < 26 categories raises; the checked-in legal snapshot stays live.
- Quota/TARIC engines stay fail-closed (`QUOTA_BALANCE_REQUIRED`,
  `TARIC_SNAPSHOT_REQUIRED`) until a fresh snapshot exists.
