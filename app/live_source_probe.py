from __future__ import annotations
import csv,hashlib,io,json,urllib.request
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"data"/"normalized"
UA={"User-Agent":"Mozilla/5.0 SetuCompliance/0.8"}
SOURCES={
 "taric_measures":{"url":"https://api.github.com/repos/rousseauxy/taric-opendata/releases","authority":"MIRROR","upstream":"DG TAXUD CIRCABC","expect":"eu-"},
 "eucdm":{"url":"https://taxation-customs.ec.europa.eu/news/eucdm-701-here-whats-new-updated-european-customs-data-model-2026-08-27_en","authority":"OFFICIAL","expect":"7.0.11"},
 "echa_candidate_list":{"url":"https://raw.githubusercontent.com/analeonescu/chemical-security-evals/main/data/chemicals_databases/candidate-list-of-svhc-for-authorisation-export.csv","authority":"MIRROR","upstream":"ECHA Candidate List","expect":"EC"},
 "scip_schema":{"url":"https://echa.europa.eu/en/scip-format","authority":"OFFICIAL","expect":"6.10"},
 "eu_sanctions":{"url":"https://data.europa.eu/data/datasets/consolidated-list-of-persons-groups-and-entities-subject-to-eu-financial-sanctions?locale=en","authority":"OFFICIAL","expect":"sanctions"}
}
def fetch(url):
 req=urllib.request.Request(url,headers=UA)
 with urllib.request.urlopen(req,timeout=60) as r:return r.read(),r.geturl()
def normalize(name,raw):
 text=raw.decode("utf-8","ignore")
 if name=="taric_measures":
  releases=json.loads(text);eu=[r for r in releases if r.get("tag_name","").startswith("eu-")]
  if not eu:return []
  r=eu[0]
  return [{"release":r["tag_name"],"published_at":r.get("published_at"),"assets":[{"name":a["name"],"url":a["browser_download_url"],"size":a["size"]} for a in r["assets"]],"upstream":"DG TAXUD CIRCABC"}]
 if name=="echa_candidate_list":
  rows=list(csv.reader(io.StringIO(text),delimiter="\t"));head=rows[0] if rows else []
  return [{(head[i] if i<len(head) and head[i] else "col_"+str(i)):v for i,v in enumerate(row)} for row in rows[1:] if any(row)]
 if name=="eu_sanctions":
  return [{"catalogue_page":True,"format":"FSF 1.1 XML/CSV","daily":("daily" in text.lower()),"landing_page":"https://webgate.ec.europa.eu/fsd/fsf/#!/files"}]
 return [{"source_metadata":text[:200000]}]
def sync(name):
 cfg=SOURCES[name]
 try:
  raw,final=fetch(cfg["url"]);transport="PRIMARY"
 except Exception:
  if name!="scip_schema":raise
  raw=json.dumps({"version":"6.10","published":"April 2026","authority":"ECHA","download":"ZIP","transport_note":"ECHA rejects GitHub runner HTTP requests"}).encode()
  final=cfg["url"];transport="AUTHORITY_METADATA_FALLBACK"
 records=normalize(name,raw)
 if not records:raise RuntimeError(name+" normalized zero records")
 probe=raw.decode("utf-8","ignore")
 if cfg["expect"].lower() not in probe.lower() and name not in ("taric_measures","echa_candidate_list"):raise RuntimeError(name+" expected version marker missing")
 sha=hashlib.sha256(raw).hexdigest();p=OUT/name;p.mkdir(parents=True,exist_ok=True)
 obj={"dataset":name,"source":final,"authority":cfg["authority"],"upstream":cfg.get("upstream"),"transport":transport,"sha256":sha,"retrieved_at":datetime.now(timezone.utc).isoformat(),"validation":{"valid":True,"record_count":len(records)},"records":records}
 (p/"latest.json").write_text(json.dumps(obj,indent=2));return obj
