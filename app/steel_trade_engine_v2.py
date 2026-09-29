from __future__ import annotations
"""2026 EU steel trade-measure engine.

The checked-in legal snapshot is usable immediately for mapped categories. A complete Annex-I
category export can be imported without code changes; unmapped CN codes fail closed.
"""
import csv,io,json
from pathlib import Path
from .eu_public_data import quota_balance
from .steel_trade_measure import evaluate_steel_entitlement
DATA=Path(__file__).resolve().parents[1]/"data"/"eu_steel_measure_2026.json"
FULL=Path(__file__).resolve().parents[1]/"data"/"eu_steel_categories_full.json"
VERSION="STEEL_QUOTA_2026_1384_1457_V2"
def import_categories(csv_text):
 cats={}
 for r in csv.DictReader(io.StringIO(csv_text)):
  k=r["category"]; x=cats.setdefault(k,{"category":k,"name":r.get("name"),"cn_codes":[]})
  x["cn_codes"].append("".join(c for c in r["cn_code"] if c.isdigit()))
  for key in ("origin_country","order_number","period_quota_t"):
   if r.get(key):x[key]=r[key]
 payload={"rule_version":VERSION,"legal_basis":["Regulation (EU) 2026/1384","Implementing Regulation (EU) 2026/1457"],"categories":list(cats.values())}; FULL.write_text(json.dumps(payload,indent=2));return payload
def category(cn):
 code="".join(c for c in str(cn) if c.isdigit())
 datasets=[json.loads(DATA.read_text())]
 if FULL.exists():datasets.insert(0,json.loads(FULL.read_text()))
 for ds in datasets:
  for x in ds["categories"]:
   if code in x.get("cn_codes",[]):return x
 return None
def evaluate(payload):
 cat=category(payload["cn_code"])
 if not cat:return {"applicable":None,"status":"PRODUCT_MAPPING_REQUIRED","claimable":False,"rule_version":VERSION,"blockers":[{"code":"STEEL_CN_MAPPING","reason":"CN code is not present in the loaded official 2026/1457 category dataset."}]}
 order=cat.get("order_number") or (cat.get("india_order_number") if str(payload["origin_country"]).upper()=="IN" else None)
 bal=payload.get("quota_remaining_t"); asof=payload.get("quota_balance_as_of"); lookup=None
 if bal is None and order:
  lookup=quota_balance(order,1,payload["import_date"])
  if lookup.get("available"):bal=lookup["record"]["balance_t"];asof=lookup["source"]["as_of"]
 result=evaluate_steel_entitlement(payload["cn_code"],payload["origin_country"],payload["import_date"],payload["customs_value_eur"],payload["quantity_t"],bal,asof)
 return {**result,"rule_version":VERSION,"quota_order_number":order,"public_quota_lookup":lookup,"legal_basis":[{"id":"2026/1384","source":"https://eur-lex.europa.eu/eli/reg/2026/1384/oj"},{"id":"2026/1457","source":"https://eur-lex.europa.eu/eli/reg_impl/2026/1457/oj/eng"}]}
