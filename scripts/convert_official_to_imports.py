"""Convert downloaded official EU reference workbooks into app-importable CSVs.

Reads data/official/*.json (published by scripts/sync_official_reference_data.py)
and writes:
  data/cbam/defaults.csv      -> POST /api/cbam/v2/defaults/import
  data/cbam/benchmarks.csv    -> POST /api/cbam/v2/benchmarks/import
  data/eu_steel_categories_full.json -> loaded automatically by steel engine

Usage: PYTHONPATH=. .venv/bin/python scripts/convert_official_to_imports.py
"""
from __future__ import annotations
import csv, io, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OFFICIAL = ROOT / "data" / "official"
CBAM_DIR = ROOT / "data" / "cbam"
CBAM_DIR.mkdir(parents=True, exist_ok=True)


def _num(v):
    if v in (None, "", "-", "N/A", "n/a", "NA"):
        return ""
    return str(v).replace(",", ".")


def convert_defaults() -> int:
    src = json.load(open(OFFICIAL / "cbam-defaults-official.json"))
    rows = src["records"]
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["country", "cn_code", "production_route", "direct", "indirect", "total"])
    n = 0
    for r in rows:
        country = r.get("sheet")
        if country in (None, "Overview", "Version History"):
            continue
        # first column key is the sheet (country) name, not col_0
        cn_raw = r.get(country) or r.get("col_0") or ""
        cn = "".join(c for c in str(cn_raw) if c.isdigit())
        if not cn or len(cn) < 4:
            continue
        if country == "_Other Countries and Territorie":
            country = "OTHER COUNTRIES AND TERRITORIES"
        direct = r.get("col_2")
        total = r.get("col_4")
        if direct in (None, "", "-") and total in (None, "", "-"):
            continue
        w.writerow([country.upper(), cn, str(r.get("col_5") or "").strip(), _num(direct), _num(r.get("col_3")), _num(total)])
        n += 1
    (CBAM_DIR / "defaults.csv").write_text(out.getvalue())
    return n


def convert_benchmarks() -> int:
    src = json.load(open(OFFICIAL / "cbam-benchmarks-official.json"))
    rows = [r for r in src["records"] if r.get("sheet") == "Benchmarks"]
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["cn_code", "production_route", "benchmark"])
    n = 0
    for r in rows:
        cn = "".join(c for c in str(r.get("CN code") or r.get("col_0") or "") if c.isdigit())
        if not cn or len(cn) < 4:
            continue
        # Column A preferred; fall back to Column B
        bm = r.get("Column A\nBMg [tCO2e/t]") or r.get("col_2") or r.get("Column B\nBMg [tCO2e/t]") or r.get("col_4")
        route = str(r.get("Column A\nProduction route indicator") or r.get("col_3") or r.get("Column B\nProduction route indicator") or r.get("col_5") or "").strip()
        if bm in (None, "", "-"):
            continue
        w.writerow([cn, route, _num(bm)])
        n += 1
    (CBAM_DIR / "benchmarks.csv").write_text(out.getvalue())
    return n


if __name__ == "__main__":
    d = convert_defaults()
    b = convert_benchmarks()
    print(json.dumps({"defaults_rows": d, "benchmarks_rows": b,
                       "defaults_csv": "data/cbam/defaults.csv",
                       "benchmarks_csv": "data/cbam/benchmarks.csv"}, indent=2))
