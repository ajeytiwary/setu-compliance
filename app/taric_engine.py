from __future__ import annotations
from datetime import date
from .eu_public_data import latest,freshness,quota_balance

RATE_TYPES={"THIRD_COUNTRY_DUTY","TARIFF_PREFERENCE","AUTONOMOUS_SUSPENSION","TARIFF_QUOTA"}
TRADE_DEFENCE={"ANTIDUMPING","COUNTERVAILING","SAFEGUARD","ADDITIONAL_DUTY"}
RESTRICTIONS={"PROHIBITION","RESTRICTION","IMPORT_CONTROL","SURVEILLANCE"}

def _cn(v):return "".join(x for x in str(v) if x.isdigit())
def _rate(v):
 if v in (None,""):return None
 s=str(v).strip().replace("%","").replace(",",".")
 try:
  n=float(s); return n/100 if n>1 else n
 except ValueError:return None
def _active(r,origin,on):
 if r.get("origin_country") not in (None,"","ALL","ERGA_OMNES",origin):return False
 d=date.fromisoformat(on)
 if r.get("valid_from") and d<date.fromisoformat(r["valid_from"]):return False
 if r.get("valid_to") and d>date.fromisoformat(r["valid_to"]):return False
 return True
def resolve_taric(cn_code,origin_country,import_date,customs_value_eur,quantity_t,documents=None,additional_code=None,max_age_days=1):
 s=latest("taric"); fr=freshness(s,max_age_days,import_date)
 base={"cn_code":_cn(cn_code),"origin_country":origin_country.upper(),"import_date":import_date,"customs_value_eur":float(customs_value_eur),"quantity_t":float(quantity_t),"freshness":fr}
 if not fr["fresh"]:return {**base,"status":"TARIC_SNAPSHOT_REQUIRED","resolved":False,"blockers":[{"code":"TARIC_FRESHNESS","reason":"Fresh TARIC snapshot required."}]}
 cn=_cn(cn_code); origin=origin_country.upper()
 matches=[r for r in s["records"] if (cn==r["cn_code"] or cn.startswith(r["cn_code"]) or r["cn_code"].startswith(cn)) and _active(r,origin,import_date)]
 if additional_code:matches=[r for r in matches if not r.get("additional_code") or r["additional_code"]==additional_code]
 docs=set(documents or []); blockers=[]; applied=[]; base_rate=None
 preferences=[]; suspensions=[]; quota_measures=[]; defence=[]; restrictions=[]
 for r in matches:
  typ=(r.get("measure_type") or "").upper(); rr=_rate(r.get("duty_rate")); req=r.get("required_document")
  if req and req not in docs:blockers.append({"code":"TARIC_DOCUMENT_REQUIRED","document":req,"measure_type":typ,"reason":r.get("condition_text") or "Supporting document/authorisation required by TARIC measure."})
  if typ=="THIRD_COUNTRY_DUTY" and rr is not None:base_rate=rr; applied.append(r)
  elif typ=="TARIFF_PREFERENCE":preferences.append(r)
  elif typ=="AUTONOMOUS_SUSPENSION":suspensions.append(r)
  elif typ=="TARIFF_QUOTA":quota_measures.append(r)
  elif typ in TRADE_DEFENCE:defence.append(r)
  elif typ in RESTRICTIONS:restrictions.append(r)
 for r in restrictions:
  if (r.get("measure_type") or "").upper()=="PROHIBITION":blockers.append({"code":"TARIC_PROHIBITION","reason":r.get("condition_text") or "Import prohibition applies."})
 rate=base_rate
 candidates=[r for r in preferences+suspensions if _rate(r.get("duty_rate")) is not None and (not r.get("required_document") or r.get("required_document") in docs)]
 if candidates:
  best=min(candidates,key=lambda x:_rate(x.get("duty_rate"))); rate=_rate(best["duty_rate"]); applied.append(best)
 quota_results=[]
 for q in quota_measures:
  order=q.get("quota_order_number")
  qb=quota_balance(order,max_age_days,import_date) if order else {"available":False}
  qr={"order_number":order,"lookup":qb,"in_quota_rate":_rate(q.get("duty_rate"))}
  if order and qb.get("available"):
   bal=float(qb["record"]["balance_t"]); qty=float(quantity_t); covered=min(qty,max(0,bal)); excess=max(0,qty-covered)
   normal=base_rate or 0; qrate=_rate(q.get("duty_rate")) or 0; unit=float(customs_value_eur)/qty if qty else 0
   qr.update({"in_quota_quantity_t":covered,"out_of_quota_quantity_t":excess,"customs_duty_eur":round(covered*unit*qrate+excess*unit*normal,2)})
  else:blockers.append({"code":"TARIC_QUOTA_BALANCE","order_number":order,"reason":"Fresh quota balance required before preferential quota treatment can be asserted."})
  quota_results.append(qr)
 normal_duty=float(customs_value_eur)*(rate if rate is not None else 0)
 defence_duty=0.0
 for r in defence:
  rr=_rate(r.get("duty_rate"))
  if rr is not None:defence_duty+=float(customs_value_eur)*rr; applied.append(r)
 if quota_results and all("customs_duty_eur" in q for q in quota_results):
  customs=min(q["customs_duty_eur"] for q in quota_results)
 else:customs=normal_duty
 return {**base,"status":"RESOLVED" if not blockers else "BLOCKED","resolved":not blockers,"third_country_rate":base_rate,"effective_base_rate":rate,"base_customs_duty_eur":round(customs,2),"trade_defence_duty_eur":round(defence_duty,2),"total_taric_duty_eur":round(customs+defence_duty,2),"quota_results":quota_results,"applicable_measures":matches,"applied_measures":applied,"blockers":blockers,"source":{"source":s["source"],"source_url":s["source_url"],"as_of":s["as_of"],"sha256":s["sha256"]},"notice":"TARIC excludes national VAT and excise; those are not included in this customs-duty total."}
