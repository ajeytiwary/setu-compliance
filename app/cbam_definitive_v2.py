from __future__ import annotations
"""CBAM definitive-period v2: actual/default emissions + free-allocation adjustment.

Reference tables are data, never invented constants. Import corrected 2025/2621/2026/1740
defaults and 2025/2620 benchmarks before a default/FAA entitlement can be asserted.
"""
import csv,io,json,os
from pathlib import Path
from .cbam_engine import calculate_actual_steel,normalize_cn
DATA=Path(os.getenv("EUROSETU_CBAM_REFERENCE_DATA","data/cbam"))
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
def import_cscf(payload):
 """Import the official uniform CSCF table (CELEX:32021D0927 / 32026D1862).

 Accepts either {"2026": 1.0, ...} or {"values": {"2026": 1.0}, "source": ...}.
 """
 values=payload.get("values") if isinstance(payload.get("values"),dict) else payload
 table={str(k):float(v) for k,v in values.items() if str(k).isdigit() and v is not None}
 if not table:raise ValueError("CSCF_TABLE_EMPTY")
 out={"source":payload.get("source") or "OFFICIAL_CSCF_TABLE","legal_basis":payload.get("legal_basis") or [],"retrieved_at":payload.get("retrieved_at"),"notes":payload.get("notes"),**table}
 return _write("cscf.json",out)
def _num(v):
 if v in (None,"","-","N/A","n/a","NA"):return None
 try:return float(str(v).replace(",","."))
 except (TypeError,ValueError):return None
def select_default(country,cn_code,production_route=None,year=2026):
 ds=_read("defaults.json")
 if not ds:return {"available":False,"reason":"CORRECTED_DEFAULT_DATA_REQUIRED"}
 cn=normalize_cn(cn_code); raw=country.upper()
 # Official default tables use full country names (INDIA, CHINA, ...).
 # Accept ISO alpha-2 codes too (IN->INDIA etc.) via pycountry when available.
 mapped=raw
 try:
  import pycountry
  if len(raw)==2:
   try:mapped=pycountry.countries.get(alpha_2=raw).name.upper()
   except Exception:pass
 except ImportError:pass
 _ISO_FALLBACK={"IN":"INDIA","CN":"CHINA","TR":"TURKIYE","KR":"KOREA, REPUBLIC OF","RU":"RUSSIAN FEDERATION","UA":"UKRAINE","GB":"UNITED KINGDOM","US":"UNITED STATES","BR":"BRAZIL","ZA":"SOUTH AFRICA","ID":"INDONESIA","MY":"MALAYSIA","TH":"THAILAND","VN":"VIET NAM","TW":"TAIWAN","JP":"JAPAN","SA":"SAUDI ARABIA","AE":"UNITED ARAB EMIRATES","EG":"EGYPT","DZ":"ALGERIA","NG":"NIGERIA","AR":"ARGENTINA","CL":"CHILE","CO":"COLOMBIA","MX":"MEXICO","CA":"CANADA","AU":"AUSTRALIA"}
 mapped=_ISO_FALLBACK.get(raw,mapped)
 countries={raw,mapped}
 def _rn(v):return str(v or "").replace("(","").replace(")","").strip().upper()
 want=_rn(production_route)
 # Official default tables list aggregated goods categories (4/6-digit).
 # Fall back from full CN to 6-digit then 4-digit prefix.
 prefixes=[cn]+([cn[:6]] if len(cn)>6 else [])+([cn[:4]] if len(cn)>4 else [])
 r=None
 for p in prefixes:
  cand=[x for x in ds["records"] if x["cn_code"]==p and (x["country"] in countries or x["country"]=="OTHER COUNTRIES AND TERRITORIES")]
  exact=[x for x in cand if x["country"] in countries]
  # Prefer exact production-route match (route-normalized: C == (C));
  # fall back to any route for that country+code (official tables are
  # route-specific, callers often omit it).
  r=(next((x for x in exact if _rn(x["production_route"])==want),None)
     or next((x for x in exact if not x["production_route"]),None)
     or next((x for x in exact),None)
     or next((x for x in cand if x["country"]=="OTHER COUNTRIES AND TERRITORIES" and (_rn(x["production_route"])==want or not x["production_route"])),None)
     or next((x for x in cand if x["country"]=="OTHER COUNTRIES AND TERRITORIES"),None))
  if r and r["total"] is not None:break
  r=None
 if not r or r["total"] is None:return {"available":False,"reason":"DEFAULT_NOT_FOUND","dataset_version":ds["version"]}
 markup=0.10 if year==2026 else 0.20 if year==2027 else 0.30
 return {"available":True,**r,"year":year,"markup":markup,"certificate_default_total":round(r["total"]*(1+markup),9),"dataset_version":ds["version"]}
def select_benchmark(cn_code,production_route=None):
 bs=_read("benchmarks.json")
 if not bs:return {"available":False,"reason":"BENCHMARK_DATA_REQUIRED"}
 cn=normalize_cn(cn_code)
 def _rn(v):return str(v or "").replace("(","").replace(")","").strip().upper()
 want=_rn(production_route)
 by_cn=[r for r in bs["records"] if r["cn_code"]==cn]
 if not by_cn:return {"available":False,"reason":"BENCHMARK_NOT_FOUND","dataset_version":bs["version"]}
 # Prefer exact route; fall back to any route for that CN when caller omits it
 # (official tables are route-specific, callers often omit it).
 cand=[r for r in by_cn if not r["production_route"] or _rn(r["production_route"])==want] or by_cn
 # 2620 requires highest benchmark where multiple steel alloy grades exist for same CN.
 r=max(cand,key=lambda x:x["benchmark"] if x["benchmark"] is not None else -1)
 return {"available":r["benchmark"] is not None,**r,"dataset_version":bs["version"]}
def _cscf(reporting_year,cscf=None):
 """Resolve the uniform cross-sectoral correction factor.

 Explicit per-call `cscf` wins; otherwise fall back to the checked-in
 official table `data/cbam/cscf.json` (CELEX:32021D0927 for 2021-2025 and
 CELEX:32026D1862 for 2026-2030, both Article 1 = 100 %). Returns
 (value, source) or (None, reason).
 """
 if cscf is not None:
  try:return float(cscf),"CALLER_PROVIDED"
  except (TypeError,ValueError):return None,"CSCF_INVALID"
 table=_read("cscf.json")
 if not table:return None,"CSCF_TABLE_REQUIRED"
 val=table.get(str(reporting_year))
 if val is None:return None,"CSCF_YEAR_UNSUPPORTED"
 try:return float(val),table.get("source","OFFICIAL_CSCF_TABLE")
 except (TypeError,ValueError):return None,"CSCF_TABLE_INVALID"
def free_allocation_adjustment(cn_code,mass_t,reporting_year,production_route=None,cscf=None):
 bm=select_benchmark(cn_code,production_route)
 if not bm["available"]:return {"available":False,"reason":bm["reason"],"benchmark":bm}
 if reporting_year not in CBAM_FACTOR:return {"available":False,"reason":"CBAM_FACTOR_YEAR_UNSUPPORTED"}
 cscf_val,cscf_src=_cscf(reporting_year,cscf)
 if cscf_val is None:return {"available":False,"reason":cscf_src,"benchmark":bm}
 sefa=CBAM_FACTOR[reporting_year]*cscf_val*bm["benchmark"]
 return {"available":True,"cbam_factor":CBAM_FACTOR[reporting_year],"cscf":cscf_val,"cscf_source":cscf_src,"benchmark":bm,"specific_embedded_free_allocation_tco2e_per_t":round(sefa,9),"free_allocation_adjustment_tco2e":round(sefa*float(mass_t),9),"legal_basis":"Implementing Regulation (EU) 2025/2620"}
def certificate_obligation(specific_emissions_tco2e_per_t,mass_t,free_allocation,certificate_price_eur=None,carbon_price_reduction_certificates=None):
 """Calculate the shipment-level certificate-equivalent obligation.

 Free-allocation adjustment is deducted from embedded emissions. A third-country
 carbon-price deduction is accepted only as an already converted number of CBAM
 certificates; EuroSetu deliberately does not invent the Article 9 conversion
 while the implementing methodology is not represented by a versioned source.
 """
 mass=float(mass_t or 0)
 if mass<=0:raise ValueError("mass_t/activity_level_t must be > 0")
 embedded=max(0.0,float(specific_emissions_tco2e_per_t))*mass
 faa=float((free_allocation or {}).get("free_allocation_adjustment_tco2e") or 0)
 after_faa=max(0.0,embedded-faa)
 reduction=0.0
 if carbon_price_reduction_certificates is not None:
  reduction=max(0.0,float(carbon_price_reduction_certificates))
 net=max(0.0,after_faa-reduction)
 price=None if certificate_price_eur is None else float(certificate_price_eur)
 return {"embedded_emissions_tco2e":round(embedded,9),"free_allocation_adjustment_tco2e":round(faa,9),"certificates_before_carbon_price_reduction":round(after_faa,9),"carbon_price_reduction_certificates":round(reduction,9),"certificates_to_surrender_estimate":round(net,9),"certificate_price_eur":price,"estimated_certificate_cost_eur":round(net*price,2) if price is not None else None,"price_basis":"CALLER_OR_OFFICIAL_SNAPSHOT_REQUIRED","legal_basis":["Regulation (EU) 2023/956 Articles 9, 21, 22","Implementing Regulation (EU) 2025/2548","Implementing Regulation (EU) 2025/2620"]}

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
 mass=payload.get("activity_level_t") or payload.get("mass_t")
 obligation=None
 if faa["available"]:
  obligation=certificate_obligation(emissions["specific_embedded_emissions_tco2e_per_t"],mass,faa,payload.get("certificate_price_eur"),payload.get("carbon_price_reduction_certificates"))
 if mode=="ACTUAL":
  verification_status=str((payload.get("verification") or {}).get("status") or "").upper()
  if verification_status!="VERIFIED":blockers.append({"reason":"ACTUAL_EMISSIONS_VERIFICATION_REQUIRED","legal_basis":"Regulation (EU) 2023/956 Article 8"})
 if payload.get("carbon_price_paid") is not None and payload.get("carbon_price_reduction_certificates") is None:
  blockers.append({"reason":"CARBON_PRICE_CONVERSION_EVIDENCE_REQUIRED","legal_basis":"Regulation (EU) 2023/956 Article 9","detail":"Provide the legally converted certificate reduction and supporting evidence; raw carbon-price currency values are not converted heuristically."})
 return {"status":"CALCULATED" if not blockers else "BLOCKED","declaration_ready":not blockers,"value_type":mode,"emissions":emissions,"free_allocation":faa,"certificate_obligation":obligation,"blockers":blockers,"rule_version":"CBAM_DEFINITIVE_V2_2547_2548_2620_2621_1740","guardrail":"Certificate cost is an estimate using a supplied/official price snapshot. Registry surrender and authority acceptance remain external."}
