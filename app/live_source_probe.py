from __future__ import annotations
import hashlib,json,urllib.request
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"data"/"normalized"
UA={"User-Agent":"Mozilla/5.0 EuroSetuCompliance/0.8"}
BROWSER_UA={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"}
TARIC_RELEASES_API="https://api.github.com/repos/rousseauxy/taric-opendata/releases"
EUCDM_ZIP_URL="https://eucdm.softdev.eu.com/EUCDM/Download/EUCDM-HTML_v7p0p11_2026-08-19.zip"
ECHA_MIRROR_URL="https://raw.githubusercontent.com/analeonescu/chemical-security-evals/main/data/chemicals_databases/candidate-list-of-svhc-for-authorisation-export.csv"
FSF_DCAT_URL="https://data.europa.eu/api/hub/search/datasets/consolidated-list-of-persons-groups-and-entities-subject-to-eu-financial-sanctions"
FSF_XML_FALLBACK="https://webgate.ec.europa.eu/fsd/fsf/public/files/xmlFullSanctionsList_1_1/content?token=dG9rZW4tMjAxNw"
FSF_CSV_FALLBACK="https://webgate.ec.europa.eu/fsd/fsf/public/files/csvFullSanctionsList_1_1/content?token=dG9rZW4tMjAxNw"
IUCLID_ARTICLE_BASE="https://raw.githubusercontent.com/USEPA/CompTox-IUCLIDTools/dev/entity_models/article_6_8/models"
IUCLID_ARTICLE_FILES=("article_9_0.py", "common_types_domain_v9.py", "platform_fields.py")
SOURCES={
 "taric_measures":{"url":TARIC_RELEASES_API,"authority":"MIRROR","upstream":"DG TAXUD CIRCABC","expect":"eu-","kind":"taric_delta_zip"},
 "eucdm":{"url":EUCDM_ZIP_URL,"authority":"MIRROR","upstream":"DG TAXUD EUCDM v7.0.11","expect":"EUCDM","kind":"eucdm_html_zip"},
 "echa_candidate_list":{"url":ECHA_MIRROR_URL,"authority":"MIRROR","upstream":"ECHA Candidate List","expect":"EC","kind":"echa_csv"},
 "scip_schema":{"url":IUCLID_ARTICLE_BASE+"/article_9_0.py","authority":"MIRROR","upstream":"IUCLID ARTICLE.9.0 dossier models (SCIP 6.10 schema/picklists)","expect":"ARTICLE","kind":"iuclid_models"},
 "eu_sanctions":{"url":FSF_DCAT_URL,"authority":"OFFICIAL","upstream":"EU FSF 1.1 consolidated list","expect":"sanctions","kind":"fsf_xml"}
}
def fetch(url,headers=None):
 req=urllib.request.Request(url,headers=headers or UA)
 with urllib.request.urlopen(req,timeout=120) as r:return r.read(),r.geturl()
def _taric_delta_url():
 import re
 raw,_=fetch(TARIC_RELEASES_API)
 for rel in json.loads(raw.decode("utf-8")):
  if not str(rel.get("tag_name","")).startswith("eu-"):continue
  deltas=sorted([a for a in rel.get("assets",[]) if re.match(r"TARIC_\d{8}_\d+\.zip$",a.get("name",""))],key=lambda a:a["name"])
  if deltas:return deltas[-1]["browser_download_url"]
 raise RuntimeError("taric_measures: no daily delta asset in mirror releases")
def _fsf_payload_url():
 try:
  raw,_=fetch(FSF_DCAT_URL)
  rec=json.loads(raw.decode("utf-8","ignore"))
  dists=rec.get("result",{}).get("distributions",[]) or []
  for d in dists:
   urls=d.get("download_url") or d.get("access_url") or []
   if isinstance(urls,str):urls=[urls]
   for u in urls:
    u=str(u)
    if "xmlFullSanctionsList_1_1" in u:return u
  for d in dists:
   urls=d.get("download_url") or d.get("access_url") or []
   if isinstance(urls,str):urls=[urls]
   for u in urls:
    if str(u).lower().endswith(".xml"):return str(u)
 except Exception:pass
 return FSF_XML_FALLBACK
def normalize(name,raw):
 from . import source_resolvers as R
 if name=="taric_measures":
  return R.normalize_taric_delta_zip(raw)["measures"]
 if name=="eucdm":
  inv=R.normalize_eucdm_html_zip(raw)
  return [{"data_element":d["data_element"],"label":d.get("label"),"source_file":d.get("source_file")} for d in inv["data_elements"]]
 if name=="echa_candidate_list":
  return R.normalize_echa_candidate_csv(raw.decode("utf-8-sig","ignore"))
 if name=="scip_schema":
  return R.normalize_iuclid_article_models(json.loads(raw.decode("utf-8")))
 if name=="eu_sanctions":
  try:return R.normalize_sanctions_xml(raw)
  except Exception:
   return R.normalize_sanctions_csv(raw.decode("utf-8-sig","ignore"))
 return [{"source_metadata":raw.decode("utf-8","ignore")[:200000]}]
def _assert_content(name,records,transport="PRIMARY"):
 """Fail closed when a payload downloads but carries no regulatory content."""
 if name=="scip_schema":
  recs=list(records)
  if not recs or recs[0].get("version")!="6.10":raise RuntimeError("scip_schema: version mismatch")
  if sum(1 for r in recs if r.get("value_code"))<100:raise RuntimeError("scip_schema: picklist codes missing")
  if sum(1 for r in recs if r.get("field"))<10:raise RuntimeError("scip_schema: field definitions missing")
  if sum(1 for r in recs if str(r.get("namespace") or "").startswith("http://iuclid6.echa.europa.eu"))<5:raise RuntimeError("scip_schema: IUCLID namespaces missing")
 if name=="taric_measures":
  good=[r for r in records if r.get("cn_code") and r.get("measure_type")]
  if len(good)<100:raise RuntimeError(f"taric_measures: only {len(good)} keyed measure rows")
 if name=="eucdm":
  des={str(r.get("data_element")) for r in records}
  if len(des)<100 or not ({"1/1","2/3","3/1"}<=des):raise RuntimeError("eucdm: declaration data elements missing")
 if name=="echa_candidate_list":
  if not (500<=len(records)<=560):raise RuntimeError(f"echa_candidate_list: unexpected count {len(records)}")
 if name=="eu_sanctions":
  good=[r for r in records if r.get("eu_reference") and (r.get("primary_name") or r.get("name"))]
  if len(good)<5000:raise RuntimeError(f"eu_sanctions: only {len(good)} identified entities")
 for r in records:
  if set(r)=={"catalogue_page"} or set(r)=={"source_metadata"}:
   raise RuntimeError(name+": transport placeholder record leaked into payload")
def _validated_fallback(name,warning):
 p=OUT/name/"latest.json"
 if not p.exists():raise RuntimeError(f"{name}: live fetch failed and no validated fallback exists: {warning}")
 obj=json.loads(p.read_text())
 validation=obj.get("validation") or {}
 if not validation.get("valid") or not obj.get("sha256") or not obj.get("records"):
  raise RuntimeError(f"{name}: fallback snapshot is not validated")
 obj={**obj,"transport":"STALE_VALIDATED_FALLBACK","sync_warning":str(warning),
      "checked_at":datetime.now(timezone.utc).isoformat()}
 return obj

def sync(name):
 cfg=SOURCES[name]
 if name=="taric_measures":
  url=_taric_delta_url();raw,final=fetch(url);transport="PRIMARY"
 elif name=="eucdm":
  try:raw,final=fetch(cfg["url"],headers=BROWSER_UA);transport="PRIMARY"
  except Exception as exc:return _validated_fallback(name,exc)
 elif name=="eu_sanctions":
  url=_fsf_payload_url()
  try:raw,final=fetch(url)
  except Exception:
   url=FSF_CSV_FALLBACK;raw,final=fetch(url)
  transport="PRIMARY"
 elif name=="scip_schema":
  files={}
  for fname in IUCLID_ARTICLE_FILES:
   blob,final=fetch(IUCLID_ARTICLE_BASE+"/"+fname)
   files[fname]=blob.decode("utf-8","ignore")
  raw=json.dumps(files,sort_keys=True).encode();transport="PRIMARY"
 else:
  raw,final=fetch(cfg["url"]);transport="PRIMARY"
 records=normalize(name,raw)
 if not records:
  if name=="eu_sanctions":return _validated_fallback(name,"live FSF payload normalized zero records")
  raise RuntimeError(name+" normalized zero records")
 _assert_content(name,records,transport)
 sha=hashlib.sha256(raw).hexdigest();p=OUT/name;p.mkdir(parents=True,exist_ok=True)
 obj={"dataset":name,"source":final,"authority":cfg["authority"],"upstream":cfg.get("upstream"),"transport":transport,"sha256":sha,"retrieved_at":datetime.now(timezone.utc).isoformat(),"validation":{"valid":True,"record_count":len(records)},"records":records}
 (p/"latest.json").write_text(json.dumps(obj,indent=2));return obj
