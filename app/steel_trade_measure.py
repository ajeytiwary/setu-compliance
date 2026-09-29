from __future__ import annotations
import json
from datetime import date
from pathlib import Path
DATA=json.loads((Path(__file__).resolve().parents[1]/"data"/"eu_steel_measure_2026.json").read_text())
def _cn(v):return "".join(x for x in str(v) if x.isdigit())
def category_for_cn(cn_code):
 c=_cn(cn_code)
 exact=next((cat for cat in DATA["categories"] if c in cat["cn_codes"]),None)
 if exact:return exact
 return None
def evaluate_steel_entitlement(cn_code,origin_country,import_date,customs_value_eur,quantity_t,quota_remaining_t=None,quota_balance_as_of=None):
 d=date.fromisoformat(import_date); start=date.fromisoformat(DATA["effective_from"]); end=date.fromisoformat(DATA["effective_to"])
 cat=category_for_cn(cn_code)
 if not cat:return {"applicable":False,"entitlement_status":"NOT_IN_STEEL_MEASURE_DATASET","cn_code":_cn(cn_code),"additional_duty_eur":0.0,"legal_basis":DATA["legal_basis"]}
 if not(start<=d<=end):return {"applicable":False,"entitlement_status":"OUTSIDE_SNAPSHOT_EFFECTIVE_PERIOD","category":cat["category"],"additional_duty_eur":0.0,"legal_basis":DATA["legal_basis"]}
 base={"applicable":True,"legal_status":"ACTIVE","category":cat["category"],"category_name":cat["name"],"cn_code":_cn(cn_code),"origin_country":origin_country,"quantity_t":float(quantity_t),"customs_value_eur":float(customs_value_eur),"out_of_quota_duty_rate":DATA["out_of_quota_duty_rate"],"legal_basis":DATA["legal_basis"],"quota_balance_source":DATA["quota_balance_source"]}
 if quota_remaining_t is None:return {**base,"entitlement_status":"QUOTA_BALANCE_REQUIRED","claimable":False,"additional_duty_eur":None,"reason":"The measure is active, but current quota balance is dynamic public customs data and must be supplied/refreshed before an in-quota entitlement can be asserted."}
 remaining=float(quota_remaining_t); qty=float(quantity_t); covered=max(0.0,min(qty,remaining)); excess=max(0.0,qty-covered); unit_value=float(customs_value_eur)/qty if qty else 0; duty=excess*unit_value*DATA["out_of_quota_duty_rate"]
 return {**base,"entitlement_status":"IN_QUOTA" if excess==0 else ("OUT_OF_QUOTA" if covered==0 else "PARTIALLY_IN_QUOTA"),"claimable":covered>0,"quota_remaining_t":remaining,"quota_balance_as_of":quota_balance_as_of,"in_quota_quantity_t":covered,"out_of_quota_quantity_t":excess,"additional_duty_eur":round(duty,2),"effective_duty_rate_on_shipment":round(duty/float(customs_value_eur),6) if customs_value_eur else 0}
def public_dataset():return DATA
