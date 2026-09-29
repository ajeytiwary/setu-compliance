from __future__ import annotations
import csv,hashlib,io,json,os,urllib.request,zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from openpyxl import load_workbook
ROOT=Path(__file__).resolve().parents[1]
CONFIG=Path(os.getenv("SETU_DATA_SOURCES",ROOT/"config"/"data_sources.json"))
CACHE=Path(os.getenv("SETU_SOURCE_CACHE",ROOT/"data"/"sources"))
@dataclass(frozen=True)
class Provider:
 dataset:str; id:str; kind:str; authority:str; legal_authority:bool; url:str; enabled:bool=True
def registry():
 return json.loads(CONFIG.read_text())["datasets"]
def providers(dataset):
 d=registry()[dataset]
 return [Provider(dataset=dataset,**p) for p in d["providers"]]
def selected(dataset,provider_id=None):
 ps=[p for p in providers(dataset) if p.enabled]
 if provider_id: ps=[p for p in ps if p.id==provider_id]
 if not ps: raise KeyError("No enabled provider for "+dataset)
 return ps[0]
def fetch(provider:Provider,timeout=60):
 req=urllib.request.Request(provider.url,headers={"User-Agent":"SetuCompliance/0.6"})
 with urllib.request.urlopen(req,timeout=timeout) as r:return r.read(),dict(r.headers)
def parse(kind,raw):
 if kind=="xlsx":
  wb=load_workbook(io.BytesIO(raw),data_only=True,read_only=True);out=[]
  for ws in wb.worksheets:
   rows=list(ws.iter_rows(values_only=True))
   if not rows:continue
   h=[str(x).strip() if x is not None else "" for x in rows[0]]
   out += [{"sheet":ws.title,**{h[i] or "col_"+str(i):v for i,v in enumerate(row) if v is not None}} for row in rows[1:]]
  return out
 if kind=="csv": return list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
 if kind=="json": return json.loads(raw)
 if kind=="zip":
  z=zipfile.ZipFile(io.BytesIO(raw));return {"files":z.namelist()}
 if kind in ("html","xml"): return {"text":raw.decode("utf-8","ignore")}
 return {"bytes":len(raw)}
def snapshot(dataset,provider_id=None,min_records=1):
 p=selected(dataset,provider_id)
 if p.kind in ("landing_page","api","external_dataset","github_release"):
  raise ValueError("Provider requires a specialized adapter: "+p.id)
 raw,headers=fetch(p);parsed=parse(p.kind,raw)
 count=len(parsed) if isinstance(parsed,list) else 1
 if count<min_records: raise ValueError("Dataset validation failed: too few records")
 sha=hashlib.sha256(raw).hexdigest();folder=CACHE/dataset;folder.mkdir(parents=True,exist_ok=True)
 obj={"dataset":dataset,"provider":p.id,"authority":p.authority,"legal_authority":p.legal_authority,"source":p.url,"sha256":sha,"record_count":count,"http":{"etag":headers.get("ETag"),"last_modified":headers.get("Last-Modified")},"records":parsed}
 (folder/"latest.json").write_text(json.dumps(obj,indent=2,default=str));return obj
def status():
 out={}
 for dataset,d in registry().items():
  path=CACHE/dataset/"latest.json"; snap=json.loads(path.read_text()) if path.exists() else None
  # Prefer the versioned manifest pointer when the resolver pipeline ran.
  try:
   from .source_resolvers import latest_manifest
   man=latest_manifest(dataset)
  except Exception:man=None
  if man and not snap:
   snap={"provider":man["provider_id"],"authority":man["authority"],"legal_authority":man["legal_authority"],"sha256":man["sha256"],"record_count":man["record_count"]}
  entry={"purpose":d["purpose"],"refresh":d["refresh"],"authority_required":d["authority_required"],"providers":[p.__dict__ for p in providers(dataset)],"snapshot":{k:snap.get(k) for k in ("provider","authority","legal_authority","sha256","record_count")} if snap else None}
  if man:entry["manifest"]=man
  out[dataset]=entry
 return out
