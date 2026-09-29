from __future__ import annotations
import base64,csv,io,json,os,urllib.parse,urllib.request,zipfile
from typing import Any
from .integrations import CONNECTORS,import_csv

def _auth_headers(prefix:str)->dict[str,str]:
    token=os.getenv(prefix+"_BEARER_TOKEN")
    if token:return {"Authorization":f"Bearer {token}","Accept":"application/json"}
    user,pw=os.getenv(prefix+"_USER"),os.getenv(prefix+"_PASSWORD")
    if user and pw:
        raw=base64.b64encode(f"{user}:{pw}".encode()).decode()
        return {"Authorization":f"Basic {raw}","Accept":"application/json"}
    return {"Accept":"application/json"}

def http_json(url:str,headers=None)->Any:
    req=urllib.request.Request(url,headers=headers or {"Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=60) as r:return json.loads(r.read().decode())

def sap_odata_pull(connector:str,url:str|None=None)->dict[str,Any]:
    prefix="SETU_"+connector.upper(); endpoint=url or os.getenv(prefix+"_URL")
    if not endpoint:raise ValueError(f"{prefix}_URL is not configured")
    fmap=json.loads(os.getenv(prefix+"_FIELD_MAP","{}")); records=[]; next_url=endpoint
    while next_url:
        payload=http_json(next_url,_auth_headers(prefix))
        batch=payload.get("value") or payload.get("d",{}).get("results") or []
        records.extend(batch)
        next_url=payload.get("@odata.nextLink") or payload.get("d",{}).get("__next")
    spec=CONNECTORS[connector]; out=io.StringIO(); w=csv.DictWriter(out,fieldnames=list(spec.required)); w.writeheader()
    for rec in records:w.writerow({f:rec.get(fmap.get(f,f),"") for f in spec.required})
    return import_csv(connector,out.getvalue(),source_name=f"SAP_ODATA:{endpoint}")

def generic_rest_pull(connector:str,prefix:str,collection_key:str)->dict[str,Any]:
    endpoint=os.getenv(prefix+"_URL")
    if not endpoint:raise ValueError(f"{prefix}_URL is not configured")
    payload=http_json(endpoint,_auth_headers(prefix)); records=payload.get(collection_key,payload if isinstance(payload,list) else [])
    spec=CONNECTORS[connector]; fmap=json.loads(os.getenv(prefix+"_FIELD_MAP","{}")); out=io.StringIO(); w=csv.DictWriter(out,fieldnames=list(spec.required)); w.writeheader()
    for rec in records:w.writerow({f:rec.get(fmap.get(f,f),"") for f in spec.required})
    return import_csv(connector,out.getvalue(),source_name=f"{prefix}_API:{endpoint}")

def generic_mes_pull():return generic_rest_pull("mes","SETU_MES","events")
def generic_ems_pull():return generic_rest_pull("ems_activity","SETU_EMS","measurements")

DAEWOO_UCI_URL="https://archive.ics.uci.edu/static/public/851/steel+industry+energy+consumption.zip"
DAEWOO_UCI_DOI="10.24432/C52G8C"
def sync_daewoo_public_ems(max_rows:int|None=None)->dict[str,Any]:
    req=urllib.request.Request(DAEWOO_UCI_URL,headers={"User-Agent":"Setu-Market-Access-OS/0.2"})
    with urllib.request.urlopen(req,timeout=60) as r:blob=r.read()
    z=zipfile.ZipFile(io.BytesIO(blob)); names=[n for n in z.namelist() if n.lower().endswith(".csv")]
    reader=csv.DictReader(io.StringIO(z.read(names[0]).decode(errors="replace"))); out=io.StringIO(); spec=CONNECTORS["scada_ems"]; w=csv.DictWriter(out,fieldnames=list(spec.required)); w.writeheader(); n=0
    for rec in reader:
        if max_rows and n>=max_rows:break
        w.writerow({"facility":"DAEWOO Steel Co. Ltd, Gwangyang (UCI public dataset)","meter_id":"KEPCO_CLOUD_ELECTRICITY","activity":"electricity_consumption","timestamp":rec.get("date") or rec.get("Date") or "","quantity":rec.get("Usage_kWh") or rec.get("Usage_kWh "),"unit":"kWh","quality":"PUBLIC_RESEARCH_DATASET"}); n+=1
    result=import_csv("scada_ems",out.getvalue(),source_name=f"UCI:{DAEWOO_UCI_DOI}")
    result["public_source"]={"company":"DAEWOO Steel Co. Ltd","doi":DAEWOO_UCI_DOI,"license":"CC BY 4.0","cbam_use":"DATA_PIPELINE_DEMO_ONLY_NOT_SUFFICIENT_FOR_CBAM"}
    return result

def connection_status():
    items=[]
    for code,prefix in [("sap_sd","SETU_SAP_SD"),("sap_mm","SETU_SAP_MM"),("mes","SETU_MES"),("ems_activity","SETU_EMS")]:
        items.append({"connector":code,"url_configured":bool(os.getenv(prefix+"_URL")),"auth_configured":bool(os.getenv(prefix+"_BEARER_TOKEN") or (os.getenv(prefix+"_USER") and os.getenv(prefix+"_PASSWORD"))),"mode":"LIVE_HTTP"})
    items.append({"connector":"daewoo_public_ems","url_configured":True,"auth_configured":True,"mode":"PUBLIC_UCI","source":DAEWOO_UCI_DOI})
    return items
