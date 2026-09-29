from __future__ import annotations
"""Public EU customs reference-data ingestion.

Adapters accept normalized JSON/CSV so deployments can consume Commission TARIC raw-data
exports and QUOTA consultation exports without coupling entitlement logic to a brittle HTML UI.
Every snapshot is hashed, timestamped and freshness-checked. Entitlement remains fail-closed.
"""
import csv,hashlib,io,json,os
from datetime import date,datetime,timezone
from pathlib import Path
from urllib.request import Request,urlopen
CACHE=Path(os.getenv("SETU_REGULATORY_CACHE","data/cache"))
TARIC_OFFICIAL="https://taxation-customs.ec.europa.eu/online-services/online-services-and-databases-customs/eu-customs-tariff-taric_en"
QUOTA_OFFICIAL="https://taxation-customs.ec.europa.eu/customs/common-customs-tariff-cct/tariff-quotas_en"
def _now():return datetime.now(timezone.utc).isoformat()
def _hash(b):return hashlib.sha256(b).hexdigest()
def _write(name,obj):
 CACHE.mkdir(parents=True,exist_ok=True); p=CACHE/name; p.write_text(json.dumps(obj,indent=2,sort_keys=True)); return str(p)
def _fetch(url):
 req=Request(url,headers={"User-Agent":"SetuCompliance/0.3 (+EU regulatory data sync)"})
 with urlopen(req,timeout=30) as r:return r.read()
def normalize_quota(rows,as_of=None):
 out=[]
 for r in rows:
  order=str(r.get("order_number") or r.get("orderNumber") or r.get("quota_order_number") or "").strip()
  if not order:continue
  def num(k):
   v=r.get(k); return None if v in (None,"") else float(str(v).replace(",",""))
  out.append({"order_number":order,"balance_t":num("balance_t"),"initial_volume_t":num("initial_volume_t"),"critical":str(r.get("critical","")).lower() in ("1","true","yes"),"status":r.get("status") or "OPEN","last_allocation_date":r.get("last_allocation_date")})
 return {"source":"EU_COMMISSION_QUOTA","source_url":QUOTA_OFFICIAL,"as_of":as_of or date.today().isoformat(),"fetched_at":_now(),"records":out}
def normalize_taric(rows,as_of=None):
 out=[]
 for r in rows:
  cn="".join(x for x in str(r.get("cn_code") or r.get("goods_code") or "") if x.isdigit())
  if not cn:continue
  out.append({"cn_code":cn,"origin_country":str(r.get("origin_country") or "").upper() or None,"measure_type":r.get("measure_type"),"duty_rate":r.get("duty_rate"),"quota_order_number":r.get("quota_order_number"),"additional_code":r.get("additional_code"),"valid_from":r.get("valid_from"),"valid_to":r.get("valid_to")})
 return {"source":"EU_COMMISSION_TARIC","source_url":TARIC_OFFICIAL,"as_of":as_of or date.today().isoformat(),"fetched_at":_now(),"records":out}
def parse_csv(text,kind,as_of=None):
 rows=list(csv.DictReader(io.StringIO(text)))
 return normalize_quota(rows,as_of) if kind=="quota" else normalize_taric(rows,as_of)
def store_snapshot(kind,data,raw=None):
 payload={**data,"sha256":_hash(raw if isinstance(raw,bytes) else json.dumps(data,sort_keys=True).encode())}
 _write(f"{kind}-latest.json",payload); return payload
def latest(kind):
 p=CACHE/f"{kind}-latest.json"
 return json.loads(p.read_text()) if p.exists() else None
def freshness(snapshot,max_age_days=1,as_of=None):
 if not snapshot:return {"fresh":False,"reason":"NO_SNAPSHOT"}
 ref=date.fromisoformat(as_of) if as_of else date.today(); d=date.fromisoformat(snapshot["as_of"])
 age=(ref-d).days; return {"fresh":age<=max_age_days and age>=0,"age_days":age,"max_age_days":max_age_days,"reason":None if age<=max_age_days and age>=0 else "STALE_OR_FUTURE_SNAPSHOT"}
def quota_balance(order_number,max_age_days=1,as_of=None):
 s=latest("quota"); fr=freshness(s,max_age_days,as_of)
 if not fr["fresh"]:return {"available":False,"freshness":fr,"source":s}
 rec=next((x for x in s["records"] if x["order_number"]==order_number),None)
 return {"available":bool(rec and rec.get("balance_t") is not None),"freshness":fr,"record":rec,"source":{"source":s["source"],"source_url":s["source_url"],"as_of":s["as_of"],"sha256":s["sha256"]}}
def sync_from_url(kind,url,as_of=None):
 raw=_fetch(url); text=raw.decode("utf-8-sig"); return store_snapshot(kind,parse_csv(text,kind,as_of),raw)
