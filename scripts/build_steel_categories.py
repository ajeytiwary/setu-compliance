#!/usr/bin/env python3
"""Build the full steel quota table from Implementing Regulation (EU) 2026/1457 Annex I.

Source: the OJ HTML table at
https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=OJ:L_202601457#anx_I
(browser-extracted DOM rows, saved to data/official/steel-2026-1457-table.json).
EUR-Lex blocks urllib (returns an empty 202), so the authoritative table is
captured via a real browser session.

The table has 285 rows: 1 header, 31 category rows (13 cells: product number,
category, CN codes, then per-country allocation), 253 continuation rows
(10 cells: country + allocation). Each category row is followed by its
country-allocation rows.

Output: data/eu_steel_categories_full.json via app.steel_trade_engine_v2.import_categories
(CSV contract: category,name,cn_code,origin_country,order_number,period_quota_t).
"""
from __future__ import annotations

import csv
import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TABLE_JSON = ROOT / "data" / "official" / "steel-2026-1457-table.json"
OUT_CSV = ROOT / "data" / "official" / "steel-2026-1457-categories.csv"


def parse_num(s: str) -> float | None:
    s = s.replace("\xa0", "").replace(" ", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def parse_table(rows: list[list[str]]) -> list[dict]:
    """Convert DOM rows into per-category dicts with country allocations."""
    categories = []
    cur = None
    for r in rows:
        if len(r) == 13 and re.match(r"^\d{1,2}(\.\s*[A-Z])?$", r[0]):
            # Category header row
            cat_key = r[0].replace(".", "").replace(" ", "")
            cn_codes = [c.replace(" ", "") for c in re.findall(r"\d{4}\s*\d{2}\s*\d{2}", r[2])]
            cur = {"category": cat_key, "name": r[1], "cn_codes": cn_codes, "countries": []}
            categories.append(cur)
            # The first country allocation may be in the same row (cols 3-12)
            if len(r) > 3 and r[3] and not re.match(r"^\d{4}\s*\d{2}\s*\d{2}", r[3]):
                cur["countries"].append({"country": r[3], "values": r[4:]})
        elif len(r) == 10 and cur is not None:
            # Continuation country allocation row
            cur["countries"].append({"country": r[0], "values": r[1:]})
    return categories


def country_block(cat: dict, country: str) -> dict | None:
    for co in cat["countries"]:
        if co["country"].lower() == country.lower():
            return co
    return None


def build_rows(categories: list[dict]) -> list[dict]:
    """One CSV row per (category, cn_code). India rows carry India's order number;
    other categories carry the 'Other countries' order number so quota lookups work."""
    rows = []
    for cat in categories:
        india = country_block(cat, "India")
        other = country_block(cat, "Other countries")
        order = None
        quota = None
        origin = "OTHER"
        if india:
            order = next((v for v in india["values"] if re.match(r"^09\.\d+$", v)), None)
            quota = parse_num(india["values"][0]) if india["values"] else None
            origin = "IN"
        elif other:
            order = next((v for v in other["values"] if re.match(r"^09\.\d+$", v)), None)
            quota = parse_num(other["values"][0]) if other["values"] else None
        for cn in cat["cn_codes"]:
            rows.append({
                "category": cat["category"],
                "name": cat["name"],
                "cn_code": cn,
                "origin_country": origin,
                "order_number": order or "",
                "period_quota_t": f"{quota:.2f}" if quota is not None else "",
            })
    return rows


def main() -> int:
    if not TABLE_JSON.exists():
        print(f"missing {TABLE_JSON}", file=sys.stderr)
        return 1
    rows = json.loads(TABLE_JSON.read_text())
    categories = parse_table(rows)
    print(f"parsed {len(categories)} categories from Annex I table")
    rows_out = build_rows(categories)
    print(f"built {len(rows_out)} CSV rows")

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["category", "name", "cn_code", "origin_country", "order_number", "period_quota_t"])
    writer.writeheader()
    writer.writerows(rows_out)
    OUT_CSV.write_text(buf.getvalue())
    print(f"wrote {OUT_CSV}")

    sys.path.insert(0, str(ROOT))
    from app.steel_trade_engine_v2 import import_categories

    payload = import_categories(buf.getvalue())
    n = len(payload["categories"])
    print(f"imported {n} categories -> data/eu_steel_categories_full.json")
    assert n >= 26, f"expected >=26 categories, got {n}"
    return 0


if __name__ == "__main__":
    raise SystemExit(main())