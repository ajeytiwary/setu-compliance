# Use cases — messy real-world inputs (link-only, synthetic derivatives)

**Honesty header:** everything under `use_cases/` is a **scenario demo**, not a
certification. Third-party pages/images are **linked, never copied** into the
repo. Messy CSVs here are **synthetic derivatives** (seed 20261002) shaped by
public document structures — they are not the third party's data.

| Use case | What it shows | Run |
|----------|---------------|-----|
| `ouco_mtc_messy/` | OUCO material-page image catalog (link-only) + Ansteel-shaped MTC messy→clean demo (receipt-style defects → BLOCKED → READY) | `python use_cases/ouco_mtc_messy/run_messy_demo.py` then `pytest -q tests/test_use_cases_messy.py` |
| `client_docs_eu_bound/` | Redacted EU-bound client extracts (steel CBAM case + non-steel contrast + MTC shape) → full pipeline BLOCKED → READY/ENTITLED, documents steel-compiler boundary | `python use_cases/client_docs_eu_bound/run_client_docs_demo.py` then `pytest -q tests/test_client_docs_use_case.py` |

Rules for every use case folder:
1. No third-party binaries (no .png/.jpg/.pdf copied). Links + sha-free catalog only.
2. Every synthetic derivative records `parent_source_url` + `synthetic_transform`.
3. Decisions go through `app.evidence_lifecycle` + `app.decision_engine`
   (`DECISION_POLICY_V1`, fail-closed) — messy input must BLOCK, never READY.
4. No positive certification / parity / guarantee language (see `scripts/lint_claims.py`).
