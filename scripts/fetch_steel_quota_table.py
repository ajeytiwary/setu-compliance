#!/usr/bin/env python3
"""Fetch the steel quota Annex I table from EUR-Lex and rebuild the full dataset.

Reproducible end-to-end update pipeline for Regulation (EU) 2026/1457 Annex I:

  1. RESOLVE: CELEX 32026R1457 -> OJ HTML URL via the Cellar semantic API
                (urllib works here; EUR-Lex itself is WAF-blocked)
  2. FETCH: the OJ HTML table. EUR-Lex blocks urllib AND headless Chrome
                (AWS WAF JS challenge), so this needs a real browser session:
                  a) --browser-json FILE : a JSON file with the table rows
                     (paste the output of scripts/extract_annex_tables.js run in
                     the browser, or the saved data/official/steel-2026-1457-table.json)
                  b) --table-index N     : which table in the JSON to use
                     (default 20 = the main Annex I table, 285x13)
  3. PARSE: DOM rows -> per-category dicts (13-cell category rows +
                10-cell country continuation rows)
  4. BUILD: one CSV row per (category, cn_code) with India order numbers
  5. IMPORT: app.steel_trade_engine_v2.import_categories -> data/eu_steel_categories_full.json

Usage:
    # Resolve the OJ URL for a CELEX number
    python scripts/resolve_eurlex_oj.py 32026R1457

    # Rebuild from a previously saved browser capture
    python scripts/fetch_steel_quota_table.py --browser-json data/official/steel-2026-1457-table.json

    # Rebuild from a fresh browser capture (paste extract_annex_tables.js output)
    python scripts/fetch_steel_quota_table.py --browser-json /tmp/annex1_tables.json --table-index 20

    # Full pipeline with CELEX resolution + browser capture
    python scripts/fetch_steel_quota_table.py --celex 32026R1457 --browser-json /tmp/annex1_tables.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.resolve_eurlex_oj import resolve_celex, oj_to_url  # noqa: E402
from scripts.build_steel_categories import parse_table, build_rows, OUT_CSV, TABLE_JSON  # noqa: E402

DEFAULT_TABLE_INDEX = 20  # main Annex I table in the OJ HTML (285 rows x 13 cols)


def pick_table(tables: list[dict], index: int | None) -> dict:
    """Select the Annex I table from a browser capture (list of {index, rows, cols})."""
    if index is not None:
        return next(t for t in tables if t["index"] == index)
    # Heuristic: the widest table with >200 rows is the Annex I quota table
    best = max(tables, key=lambda t: (t.get("rows", 0) if isinstance(t.get("rows"), int) else len(t.get("rows", []))))
    return best


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--celex", help="CELEX number to resolve (e.g. 32026R1457)")
    ap.add_argument("--browser-json", required=True, help="JSON file with browser-captured tables (extract_annex_tables.js output) or raw rows")
    ap.add_argument("--table-index", type=int, default=None, help="table index to use (default: auto-detect widest)")
    ap.add_argument("--save-table", default=str(TABLE_JSON), help="where to save the raw table JSON")
    args = ap.parse_args()

    # 1. Resolve CELEX -> OJ URL
    if args.celex:
        ojs = resolve_celex(args.celex)
        if not ojs:
            print(f"ERROR: no OJ resource found for CELEX {args.celex}", file=sys.stderr)
            return 1
        url = oj_to_url(ojs[0])
        print(f"[1/5] resolved CELEX {args.celex} -> {url}")
    else:
        url = oj_to_url("L_202601457")
        print(f"[1/5] using default OJ URL: {url}")

    # 2. Load browser capture
    raw = json.loads(Path(args.browser_json).read_text())
    if isinstance(raw, list) and raw and isinstance(raw[0], list):
        # Raw rows (e.g. saved steel-2026-1457-table.json)
        rows = raw
        print(f"[2/5] loaded {len(rows)} raw rows from {args.browser_json}")
    elif isinstance(raw, dict) and "tables" in raw:
        tables = raw["tables"]
        table = pick_table(tables, args.table_index)
        rows = table["rows"]
        print(f"[2/5] loaded table index {table.get('index')} ({len(rows)} rows x {table.get('cols')}) from {args.browser_json}")
    else:
        print("ERROR: unrecognized browser capture format", file=sys.stderr)
        return 1

    # 3. Parse
    categories = parse_table(rows)
    print(f"[3/5] parsed {len(categories)} categories from Annex I table")

    # 4. Build CSV rows
    rows_out = build_rows(categories)
    print(f"[4/5] built {len(rows_out)} CSV rows")

    # 5. Import
    import csv, io
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["category", "name", "cn_code", "origin_country", "order_number", "period_quota_t"])
    writer.writeheader()
    writer.writerows(rows_out)
    OUT_CSV.write_text(buf.getvalue())

    from app.steel_trade_engine_v2 import import_categories
    payload = import_categories(buf.getvalue())
    n = len(payload["categories"])
    print(f"[5/5] imported {n} categories -> data/eu_steel_categories_full.json")

    # Save the raw table for reproducibility
    Path(args.save_table).write_text(json.dumps(rows, indent=1))
    print(f"      saved raw table -> {args.save_table}")

    assert n >= 26, f"expected >=26 categories, got {n}"
    print("OK: steel quota dataset rebuilt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())