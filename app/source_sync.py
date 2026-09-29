from __future__ import annotations
import csv,hashlib,io,json,os,re,shutil,urllib.parse,urllib.request,zipfile
from datetime import datetime,timezone
from pathlib import Path
from xml.etree import ElementTree as ET
from .data_sources import ROOT,registry,selected
RAW=Path(os.getenv("SETU_RAW_DATA",ROOT/"data"/"raw")); NORMALIZED=Path(os.getenv("SETU_NORMALIZED_DATA",ROOT/"data"/"normalized")); MANIFESTS=Path(os.getenv("SETU_MANIFESTS",ROOT/"data"/"manifests"))
UA={"User-Agent":"SetuCompliance/0.7 (+regulatory-data-sync)"}
def now():return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
def get(url,timeout=90):
 req=urllib.request.Request(url,headers=UA)
 with urllib.request.urlopen(req,timeout=timeout) as r:return r.read(),dict(r.headers),r.geturl()
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
 rows=list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))));out=[]
 for r in rows:
  def pick(*names):
   for n in names:
    for k,v in r.items():
     if n in k.lower() and v:return v.strip()
   return None
  out.append({"name":pick("substance name","name"),"ec_number":pick("ec number","ec no"),"cas_number":pick("cas number","cas no"),"reason":pick("reason"),"included_at":pick("date of inclusion","inclusion")})
 return [x for x in out if x["name"] or x["ec_number"]]
def normalize_sanctions(raw,fmt):
 if fmt=="csv":
  rows=list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))));out=[]
  for r in rows:
   low={k.lower():v for k,v in r.items()}
   ref=next((v for k,v in low.items() if ("eu reference" in k or "entity_logical_id" in k or k=="logicalid") and v),None)
   name=next((v for k,v in low.items() if ("whole name" in k or k=="name") and v),None)
   out.append({"eu_reference":ref,"entity_type":next((v for k,v in low.items() if "entity" in k and "type" in k and v),None),"name":name,"aliases":[],"identifiers":[],"programme":next((v for k,v in low.items() if "programme" in k and v),None),"legal_basis":next((v for k,v in low.items() if "regulation" in k and v),None)})
  return [x for x in out if x["eu_reference"] or x["name"]]
 root=ET.fromstring(raw);out=[]
 for el in root.iter():
  row=flatten_xml(el);name=row.get("wholename") or row.get("name");ref=row.get("eureference") or row.get("logicalid")
  if name and ref:out.append({"eu_reference":ref,"entity_type":row.get("entitytype"),"name":name,"aliases":[],"identifiers":[],"programme":row.get("programme"),"legal_basis":row.get("regulation")})
 return out
def normalize_eucdm(raw):
 z=zipfile.ZipFile(io.BytesIO(raw));records=[]
 for name in z.namelist():
  if not name.lower().endswith(".xml"):continue
  try:root=ET.fromstring(z.read(name))
  except Exception:continue
  for el in root.iter():
   row=flatten_xml(el);de=row.get("dataelement") or row.get("dataelementid") or row.get("dataelementnumber")
   if de:records.append({"data_element":de,"label":row.get("name") or row.get("label") or row.get("description"),"format":row.get("format"),"cardinality":row.get("cardinality"),"code_list":row.get("codelist") or row.get("codelistid"),"procedure":row.get("procedure"),"source_file":name})
 return records
def normalize_scip(raw):
 z=zipfile.ZipFile(io.BytesIO(raw));names=z.namelist()
 return [{"version":"6.10","picklists":[n for n in names if "pick" in n.lower()],"validation_rules":[n for n in names if "valid" in n.lower()],"schema_files":[n for n in names if n.lower().endswith((".xsd",".xml"))],"files":names}]
def normalize_taric(raw):
 z=zipfile.ZipFile(io.BytesIO(raw));records=[]
 for name in z.namelist():
  if not name.lower().endswith(".xml"):continue
  try:root=ET.fromstring(z.read(name))
  except Exception:continue
  for el in root.iter():
   row=flatten_xml(el)
   cn=row.get("goodsnomenclatureitemid") or row.get("commoditycode")
   mt=row.get("measuretypeid") or row.get("measuretype")
   if cn and mt:records.append({"cn_code":re.sub(r"\D","",cn),"origin_country":row.get("geographicalareaid"),"measure_type":mt,"duty_rate":row.get("dutyexpression") or row.get("dutyamount"),"quota_order_number":row.get("quotaordernumberid"),"additional_code":row.get("additionalcodeid"),"required_document":row.get("certificatecode"),"valid_from":row.get("validitystartdate"),"valid_to":row.get("validityenddate"),"legal_basis":row.get("regulationid"),"source_file":name})
 return records
def resolve(dataset):
 p=selected(dataset)
 if dataset=="echa_candidate_list":
  u=discover(p.url,[lambda u:u.lower().endswith(".csv") and ("2026" in u or "candidate" in u.lower()),lambda u:u.lower().endswith(".csv")]);return u,"csv",normalize_candidate_csv
 if dataset=="scip_schema":
  u=discover(p.url,[lambda u:u.lower().endswith(".zip") and ("6.10" in u or "610" in u),lambda u:u.lower().endswith(".zip")]);return u,"zip",normalize_scip
 if dataset=="eu_sanctions":
  # data.europa.eu DCAT API exposes distributions; HTML fallback keeps resolver portable.
  u=discover(p.url,[lambda u:("1.1" in u or "1_1" in u) and u.lower().endswith(".xml"),lambda u:("1.1" in u or "1_1" in u) and u.lower().endswith(".csv"),lambda u:u.lower().endswith(".xml"),lambda u:u.lower().endswith(".csv")]);fmt="xml" if u.lower().endswith(".xml") else "csv";return u,fmt,lambda b:normalize_sanctions(b,fmt)
 if dataset=="eucdm":
  u=discover(p.url,[lambda u:u.lower().endswith(".zip") and ("7.0.11" in u or "7011" in u or "download" in u.lower()),lambda u:u.lower().endswith(".zip")]);return u,"zip",normalize_eucdm
 if dataset=="taric_measures":
  # Prefer configured direct bulk URL. For official landing pages, resolve a ZIP/XML distribution if exposed.
  direct=os.getenv("SETU_TARIC_BULK_URL")
  if direct:return direct,"zip",normalize_taric
  u=discover(p.url,[lambda u:u.lower().endswith(".zip") and "taric" in u.lower(),lambda u:u.lower().endswith(".zip")]);return u,"zip",normalize_taric
 raise KeyError(dataset)
def validate(dataset,records):
 errors=[]
 if not records:errors.append("NO_NORMALIZED_RECORDS")
 if dataset=="echa_candidate_list" and len(records)<500:errors.append("CANDIDATE_LIST_UNEXPECTEDLY_SMALL")
 if dataset=="eu_sanctions" and len(records)<100:errors.append("SANCTIONS_UNEXPECTEDLY_SMALL")
 if dataset=="eucdm" and len(records)<50:errors.append("EUCDM_UNEXPECTEDLY_SMALL")
 if dataset=="taric_measures" and len(records)<1000:errors.append("TARIC_UNEXPECTEDLY_SMALL")
 if dataset=="scip_schema" and (not records or records[0].get("version")!="6.10"):errors.append("SCIP_VERSION_MISMATCH")
 return {"valid":not errors,"errors":errors,"record_count":len(records)}
def sync(dataset):
 p=selected(dataset);url,fmt,normalizer=resolve(dataset);raw,headers,final=get(url);sha=hashlib.sha256(raw).hexdigest();stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
 rawdir=RAW/dataset/sha;rawdir.mkdir(parents=True,exist_ok=True);filename=safe_name(final,"source."+fmt);(rawdir/filename).write_bytes(raw)
 records=normalizer(raw);check=validate(dataset,records)
 manifest={"dataset":dataset,"provider":p.id,"authority":p.authority,"legal_authority":p.legal_authority,"source":final,"retrieved_at":now(),"sha256":sha,"content_type":headers.get("Content-Type"),"etag":headers.get("ETag"),"last_modified":headers.get("Last-Modified"),"parser_version":"setu-source-sync-0.7","validation":check,"raw_file":str((rawdir/filename).relative_to(ROOT))}
 mdir=MANIFESTS/dataset;mdir.mkdir(parents=True,exist_ok=True);(mdir/(sha+".json")).write_text(json.dumps(manifest,indent=2))
 if not check["valid"]:raise RuntimeError(dataset+" validation failed: "+",".join(check["errors"]))
 ndir=NORMALIZED/dataset/sha;ndir.mkdir(parents=True,exist_ok=True);(ndir/"records.json").write_text(json.dumps(records,indent=2,default=str))
 latest=NORMALIZED/dataset/"latest.json";tmp=NORMALIZED/dataset/(".latest-"+stamp+".tmp");tmp.write_text(json.dumps({**manifest,"normalized_file":str((ndir/"records.json").relative_to(ROOT))},indent=2));os.replace(tmp,latest)
 return json.loads(latest.read_text())
def sync_many(datasets):
 result={}
 for d in datasets:
  try:result[d]={"ok":True,"snapshot":sync(d)}
  except Exception as e:result[d]={"ok":False,"error":str(e)}
 return result
