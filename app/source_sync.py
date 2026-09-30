from __future__ import annotations
import csv,hashlib,io,json,os,re,shutil,urllib.parse,urllib.request,zipfile
from datetime import datetime,timezone
from pathlib import Path
from xml.etree import ElementTree as ET
from .data_sources import ROOT,registry,selected
RAW=Path(os.getenv("SETU_RAW_DATA",ROOT/"data"/"raw")); NORMALIZED=Path(os.getenv("SETU_NORMALIZED_DATA",ROOT/"data"/"normalized")); MANIFESTS=Path(os.getenv("SETU_MANIFESTS",ROOT/"data"/"manifests"))
UA={"User-Agent":"SetuCompliance/0.7 (+regulatory-data-sync)"}
BROWSER_UA={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"}
# Direct versioned distributions (verified 2026-09-30). Landing pages expose
# no file links, so resolvers fetch these payloads instead of link-discovery.
TARIC_RELEASES_API="https://api.github.com/repos/rousseauxy/taric-opendata/releases"
EUCDM_ZIP_URL="https://eucdm.softdev.eu.com/EUCDM/Download/EUCDM-HTML_v7p0p11_2026-08-19.zip"
ECHA_MIRROR_URL="https://raw.githubusercontent.com/analeonescu/chemical-security-evals/main/data/chemicals_databases/candidate-list-of-svhc-for-authorisation-export.csv"
FSF_DCAT_URL="https://data.europa.eu/api/hub/search/datasets/consolidated-list-of-persons-groups-and-entities-subject-to-eu-financial-sanctions"
FSF_XML_FALLBACK="https://webgate.ec.europa.eu/fsd/fsf/public/files/xmlFullSanctionsList_1_1/content?token=dG9rZW4tMjAxNw"
FSF_CSV_FALLBACK="https://webgate.ec.europa.eu/fsd/fsf/public/files/csvFullSanctionsList_1_1/content?token=dG9rZW4tMjAxNw"
# SCIP 6.10 schema/picklist payload (ECHA blocks automated fetches with Azure
# WAF 403, so the official ZIP is browser-only). Downloadable mirror: the
# IUCLID ARTICLE.9.0 dossier models SCIP notifications are built on, from the
# USEPA CompTox IUCLIDTools dev branch (real namespaces, field definitions,
# Pg* picklist enums -- not metadata).
IUCLID_ARTICLE_BASE="https://raw.githubusercontent.com/USEPA/CompTox-IUCLIDTools/dev/entity_models/article_6_8/models"
IUCLID_ARTICLE_FILES=("article_9_0.py", "common_types_domain_v9.py", "platform_fields.py")
def now():return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
def get(url,timeout=90,headers=None):
 req=urllib.request.Request(url,headers=headers or UA)
 with urllib.request.urlopen(req,timeout=timeout) as r:return r.read(),dict(r.headers),r.geturl()
def _github_json(url,timeout=90):
 raw,_,_=get(url,timeout)
 return json.loads(raw.decode("utf-8"))
def _taric_latest_delta_asset():
 """Newest daily TARIC_<date>.zip asset from the mirror releases API."""
 for rel in _github_json(TARIC_RELEASES_API):
  if not str(rel.get("tag_name","")).startswith("eu-"):continue
  deltas=sorted([a for a in rel.get("assets",[]) if re.match(r"TARIC_\d{8}_\d+\.zip$",a.get("name",""))],key=lambda a:a["name"])
  if deltas:return deltas[-1]["browser_download_url"],"zip"
 raise RuntimeError("No TARIC daily delta asset in mirror releases")
def _fsf_download_url(prefer="xml"):
 """Resolve the FSF payload via the data.europa DCAT record; fall back to
 the known webgate token URLs when the catalogue API is unreachable."""
 try:
  rec=_github_json(FSF_DCAT_URL)
  dists=rec.get("result",{}).get("distributions",[]) or []
  urls=[]
  for d in dists:
   u=d.get("download_url") or d.get("access_url") or []
   urls+=([u] if isinstance(u,str) else list(u))
  urls=[str(u) for u in urls]
  if prefer=="xml":
   for u in urls:
    if "xmlFullSanctionsList_1_1" in u:return u,"xml"
   for u in urls:
    if u.lower().endswith(".xml"):return u,"xml"
  else:
   for u in urls:
    if "csvFullSanctionsList_1_1" in u:return u,"csv"
   for u in urls:
    if u.lower().endswith(".csv"):return u,"csv"
 except Exception:pass
 return (FSF_XML_FALLBACK,"xml") if prefer=="xml" else (FSF_CSV_FALLBACK,"csv")
def links(base,html):
 out=[]
 for href in re.findall(r'''href=["']([^"']+)''',html,re.I):
  out.append(urllib.parse.urljoin(base,href.replace("&amp;","&")))
 return list(dict.fromkeys(out))
def discover(page_url,predicates):
 raw,_,final=get(page_url);html=raw.decode("utf-8","ignore");ls=links(final,html)
 for pred in predicates:
  matches=[u for u in ls if pred(u)]
  if matches:return matches[0]
 raise RuntimeError("No matching official distribution found at "+page_url)
def safe_name(url,default):
 n=Path(urllib.parse.urlparse(url).path).name
 return n or default
def text_local(tag):return tag.rsplit("}",1)[-1].lower()
def flatten_xml(el):
 row={}
 for x in el.iter():
  if x is el:continue
  t=(x.text or "").strip()
  if t and len(list(x))==0:row[text_local(x.tag)]=t
 return row
def normalize_candidate_csv(raw):
 from .source_resolvers import normalize_echa_candidate_csv
 return normalize_echa_candidate_csv(raw.decode("utf-8-sig", "ignore"))
def normalize_sanctions(raw,fmt):
 from . import source_resolvers as R
 if fmt=="csv":
  return R.normalize_sanctions_csv(raw.decode("utf-8-sig", "ignore"))
 return R.normalize_sanctions_xml(raw)
def normalize_eucdm(raw):
 from .source_resolvers import normalize_eucdm_html_zip
 inv=normalize_eucdm_html_zip(raw)
 return [{"data_element":d["data_element"],"label":d.get("label"),"source_file":d.get("source_file")} for d in inv["data_elements"]]
def normalize_scip(raw):
 z=zipfile.ZipFile(io.BytesIO(raw));names=z.namelist()
 return [{"version":"6.10","picklists":[n for n in names if "pick" in n.lower()],"validation_rules":[n for n in names if "valid" in n.lower()],"schema_files":[n for n in names if n.lower().endswith((".xsd",".xml"))],"files":names}]
def normalize_scip_iuclid(files):
 from .source_resolvers import normalize_iuclid_article_models
 return normalize_iuclid_article_models(files)
def _fetch_iuclid_article_models():
 from .source_resolvers import normalize_iuclid_article_models
 files={}
 for fname in IUCLID_ARTICLE_FILES:
  raw,_,_=get(IUCLID_ARTICLE_BASE+"/"+fname)
  files[fname]=raw.decode("utf-8","ignore")
 return normalize_iuclid_article_models(files),files
def normalize_taric(raw):
 from .source_resolvers import normalize_taric_delta_zip
 inv=normalize_taric_delta_zip(raw)
 return inv["measures"]
def resolve(dataset):
 if dataset=="echa_candidate_list":
  return ECHA_MIRROR_URL,"csv",normalize_candidate_csv
 if dataset=="scip_schema":
  # Primary: downloadable IUCLID ARTICLE.9.0 models (SCIP schema/picklists).
  # Manual --file ingest of the official ECHA SCIP 6.10 ZIP stays available
  # via scripts/sync_sources.py --dataset scip_schema --file.
  return IUCLID_ARTICLE_BASE+"/article_9_0.py","iuclid-models",None
 if dataset=="eu_sanctions":
  u,fmt=_fsf_download_url("xml")
  try:get(u,timeout=30)
  except Exception:u,fmt=_fsf_download_url("csv")
  return u,fmt,lambda b:normalize_sanctions(b,fmt)
 if dataset=="eucdm":
  return EUCDM_ZIP_URL,"zip",normalize_eucdm
 if dataset=="taric_measures":
  # Prefer configured direct bulk URL, else newest daily delta from the mirror.
  direct=os.getenv("SETU_TARIC_BULK_URL")
  if direct:return direct,"zip",normalize_taric
  u,fmt=_taric_latest_delta_asset();return u,fmt,normalize_taric
 raise KeyError(dataset)
def validate(dataset,records):
 errors=[]
 if not records:errors.append("NO_NORMALIZED_RECORDS")
 if dataset=="echa_candidate_list":
  if not (500<=len(records)<=560):errors.append("CANDIDATE_LIST_UNEXPECTED_COUNT")
  if sum(1 for r in records if r.get("substance_name"))<500:errors.append("CANDIDATE_LIST_MISSING_NAMES")
 if dataset=="eu_sanctions":
  if len(records)<5000:errors.append("SANCTIONS_UNEXPECTEDLY_SMALL")
  if sum(1 for r in records if r.get("eu_reference") and (r.get("primary_name") or r.get("name")))<5000:errors.append("SANCTIONS_MISSING_IDENTITY")
 if dataset=="eucdm":
  if len(records)<100:errors.append("EUCDM_UNEXPECTEDLY_SMALL")
  des={str(r.get("data_element")) for r in records}
  if not ({"1/1","2/3","3/1"}<=des):errors.append("EUCDM_MISSING_CORE_DES")
 if dataset=="taric_measures":
  if len(records)<100:errors.append("TARIC_UNEXPECTEDLY_SMALL")
  if sum(1 for r in records if r.get("cn_code") and r.get("measure_type"))<100:errors.append("TARIC_MISSING_MEASURE_KEYS")
 if dataset=="scip_schema":
  if not records or records[0].get("version")!="6.10":errors.append("SCIP_VERSION_MISMATCH")
  else:
   recs=list(records)
   if sum(1 for r in recs if r.get("value_code"))<100:errors.append("SCIP_MISSING_PICKLIST_CODES")
   if sum(1 for r in recs if r.get("field"))<10:errors.append("SCIP_MISSING_FIELD_DEFINITIONS")
   if sum(1 for r in recs if str(r.get("namespace") or "").startswith("http://iuclid6.echa.europa.eu"))<10:errors.append("SCIP_MISSING_NAMESPACES")
 return {"valid":not errors,"errors":errors,"record_count":len(records)}
def _sync_scip_iuclid(p):
 """Versioned sync of the IUCLID ARTICLE.9.0 model files (SCIP payload)."""
 files={}
 for fname in IUCLID_ARTICLE_FILES:
  raw,_,_=get(IUCLID_ARTICLE_BASE+"/"+fname)
  files[fname]=raw.decode("utf-8","ignore")
 from .source_resolvers import normalize_iuclid_article_models
 records=normalize_iuclid_article_models(files)
 check=validate("scip_schema",records)
 blob=json.dumps(files,sort_keys=True).encode()
 sha=hashlib.sha256(blob).hexdigest();stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
 rawdir=RAW/"scip_schema"/sha;rawdir.mkdir(parents=True,exist_ok=True)
 for fname,text in files.items():(rawdir/fname).write_text(text)
 manifest={"dataset":"scip_schema","provider":p.id,"authority":"MIRROR","legal_authority":False,"source":IUCLID_ARTICLE_BASE,"retrieved_at":now(),"sha256":sha,"content_type":"text/x-python","parser_version":"setu-source-sync-0.9","validation":check,"raw_file":str((rawdir/"article_9_0.py").relative_to(ROOT))}
 mdir=MANIFESTS/"scip_schema";mdir.mkdir(parents=True,exist_ok=True);(mdir/(sha+".json")).write_text(json.dumps(manifest,indent=2))
 if not check["valid"]:raise RuntimeError("scip_schema validation failed: "+",".join(check["errors"]))
 ndir=NORMALIZED/"scip_schema"/sha;ndir.mkdir(parents=True,exist_ok=True);(ndir/"records.json").write_text(json.dumps(records,indent=2,default=str))
 latest=NORMALIZED/"scip_schema"/"latest.json";tmp=NORMALIZED/"scip_schema"/(".latest-"+stamp+".tmp");tmp.write_text(json.dumps({**manifest,"transport":"PRIMARY","normalized_file":str((ndir/"records.json").relative_to(ROOT)),"records":records},indent=2));os.replace(tmp,latest)
 return json.loads(latest.read_text())
def sync(dataset):
 p=selected(dataset)
 if dataset=="scip_schema":
  return _sync_scip_iuclid(p)
 url,fmt,normalizer=resolve(dataset)
 req_headers=BROWSER_UA if dataset=="eucdm" else None
 raw,resp_headers,final=get(url,headers=req_headers);sha=hashlib.sha256(raw).hexdigest();stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
 rawdir=RAW/dataset/sha;rawdir.mkdir(parents=True,exist_ok=True);filename=safe_name(final,"source."+fmt);(rawdir/filename).write_bytes(raw)
 records=normalizer(raw);check=validate(dataset,records)
 manifest={"dataset":dataset,"provider":p.id,"authority":p.authority,"legal_authority":p.legal_authority,"source":final,"retrieved_at":now(),"sha256":sha,"content_type":resp_headers.get("Content-Type"),"etag":resp_headers.get("ETag"),"last_modified":resp_headers.get("Last-Modified"),"parser_version":"setu-source-sync-0.8","validation":check,"raw_file":str((rawdir/filename).relative_to(ROOT))}
 mdir=MANIFESTS/dataset;mdir.mkdir(parents=True,exist_ok=True);(mdir/(sha+".json")).write_text(json.dumps(manifest,indent=2))
 if not check["valid"]:raise RuntimeError(dataset+" validation failed: "+",".join(check["errors"]))
 ndir=NORMALIZED/dataset/sha;ndir.mkdir(parents=True,exist_ok=True);(ndir/"records.json").write_text(json.dumps(records,indent=2,default=str))
 latest=NORMALIZED/dataset/"latest.json";tmp=NORMALIZED/dataset/(".latest-"+stamp+".tmp");tmp.write_text(json.dumps({**manifest,"transport":"PRIMARY","normalized_file":str((ndir/"records.json").relative_to(ROOT)),"records":records},indent=2));os.replace(tmp,latest)
 return json.loads(latest.read_text())
def sync_many(datasets):
 result={}
 for d in datasets:
  try:result[d]={"ok":True,"snapshot":sync(d)}
  except Exception as e:result[d]={"ok":False,"error":str(e)}
 return result
