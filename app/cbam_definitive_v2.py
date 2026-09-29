from __future__ import annotations
"""CBAM definitive-period v2: actual/default emissions + free-allocation adjustment.

Reference tables are data, never invented constants. Import corrected 2025/2621/2026/1740
defaults and 2025/2620 benchmarks before a default/FAA entitlement can be asserted.
"""
import csv,io,json,os
from pathlib import Path
from .cbam_engine import calculate_actual_steel,normalize_cn
DATA=Path(os.getenv("SETU_CBAM_REFERENCE_DATA","data/cbam"))
DATA.mkdir(parents=True,exist_ok=True)
CBAM_FACTOR={2026:0.975,2027:0.95,2028:0.90,2029:0.775,2030:0.515,2031:0.39,2032:0.265,2033:0.14,2034:0.0}
def _read(name):
 p=DATA/name; return json.loads(p.read_text()) if p.exists() else None
def _write(name,obj):DATA.mkdir(parents=True,exist_ok=True);(DATA/name).write_text(json.dumps(obj,indent=2,sort_keys=True));return obj
def import_defaults(csv_text,version="2025/2621-corrected-2026/1740"):
 rows=[]
 for r in csv.DictReader(io.StringIO(csv_text)):
  cn=normalize_cn(r.get("cn_code") or r.get("taric_code"))
  if not cn:continue
  rows.append({"country":(r.get("country") or "").upper(),"cn_code":cn,"production_route":r.get("production_route") or None,"direct":_num(r.get("direct")),"indirect":_num(r.get("indirect")),"total":_num(r.get("total"))})
 return _write("defaults.json",{"version":version,"legal_basis":["2025/2621","2026/1740"],"records":rows})
def import_benchmarks(csv_text,version="2025/2620"):
 rows=[]
 for r in csv.DictReader(io.StringIO(csv_text)):
  cn=normalize_cn(r.get("cn_code")); rows.append({"cn_code":cn,"production_route":r.get("production_route") or None,"benchmark":_num(r.get("benchmark"))})
 return _write("benchmarks.json",{"version":version,"legal_basis":["2025/2620"],"records":rows})
def _num(v):
 if v in (None,"","-"):return None
 return float(str(v).replace(",","."))
def select_default(country,cn_code,production_route=None,year=2026):
 ds=_read("defaults.json")
 if not ds:return {"available":False,"reason":"CORRECTED_DEFAULT_DATA_REQUIRED"}
 cn=normalize_cn(cn_code); country=country.upper()
 cand=[r for r in ds["records"] if r["cn_code"]==cn and r["country"] in (country,"OTHER COUNTRIES AND TERRITORIES")]
 exact=[r for r in cand if r["country"]==country]
 r=next((x for x in exact if not x["production_route"] or x["production_route"]==production_route),None) or next((x for x in cand if x["country"]=="OTHER COUNTRIES AND TERRITORIES" and (not x["production_route"] or x["production_route"]==production_route)),None)
 if not r or r["total"] is None:return {"available":False,"reason":"DEFAULT_NOT_FOUND","dataset_version":ds["version"]}
 markup=0.10 if year==2026 else 0.20 if year==2027 else 0.30
 return {"available":True,**r,"year":year,"markup":markup,"certificate_default_total":round(r["total"]*(1+markup),9),"dataset_version":ds["version"]}
def select_benchmark(cn_code,production_route=None):
 bs=_read("benchmarks.json")
 if not bs:return {"available":False,"reason":"BENCHMARK_DATA_REQUIRED"}
 cn=normalize_cn(cn_code); cand=[r for r in bs["records"] if r["cn_code"]==cn and (not r["production_route"] or r["production_route"]==production_route)]
 if not cand:return {"available":False,"reason":"BENCHMARK_NOT_FOUND","dataset_version":bs["version"]}
 # 2620 requires highest benchmark where multiple steel alloy grades exist for same CN.
 r=max(cand,key=lambda x:x["benchmark"] if x["benchmark"] is not None else -1)
 return {"available":r["benchmark"] is not None,**r,"dataset_version":bs["version"]}
def free_allocation_adjustment(cn_code,mass_t,reporting_year,production_route=None,cscf=None):
 bm=select_benchmark(cn_code,production_route)
 if not bm["available"]:return {"available":False,"reason":bm["reason"],"benchmark":bm}
 if reporting_year not in CBAM_FACTOR:return {"available":False,"reason":"CBAM_FACTOR_YEAR_UNSUPPORTED"}
 if cscf is None:return {"available":False,"reason":"CSCF_REQUIRED","benchmark":bm}
 sefa=CBAM_FACTOR[reporting_year]*float(cscf)*bm["benchmark"]
 return {"available":True,"cbam_factor":CBAM_FACTOR[reporting_year],"cscf":float(cscf),"benchmark":bm,"specific_embedded_free_allocation_tco2e_per_t":round(sefa,9),"free_allocation_adjustment_tco2e":round(sefa*float(mass_t),9),"legal_basis":"Implementing Regulation (EU) 2025/2620"}
def calculate(payload):
 mode=str(payload.get("value_type","ACTUAL")).upper(); year=int(payload.get("reporting_period") or payload.get("year") or 2026)
 if mode=="ACTUAL":
  emissions=calculate_actual_steel(payload)
 else:
  d=select_default(payload["origin_country"],payload["cn_code"],payload.get("production_route"),year)
  if not d["available"]:return {"status":"BLOCKED","blockers":[d],"value_type":"DEFAULT"}
  emissions={"specific_embedded_emissions_tco2e_per_t":d["certificate_default_total"],"default":d}
 faa=free_allocation_adjustment(payload["cn_code"],payload.get("activity_level_t") or payload.get("mass_t"),year,payload.get("production_route"),payload.get("cscf"))
 blockers=[] if faa["available"] else [faa]
 return {"status":"CALCULATED" if not blockers else "BLOCKED","value_type":mode,"emissions":emissions,"free_allocation":faa,"blockers":blockers,"rule_version":"CBAM_DEFINITIVE_V2_2547_2620_2621_1740"}
