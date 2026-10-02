#!/usr/bin/env python3
"""Build/rebuild the EuroSetu public trade-evidence corpus.

Default is OFFLINE: creates deterministic synthetic evidence room + manifest.
--acquire downloads only explicitly direct-download sources. Landing pages/APIs are
recorded for adapters and never scraped opportunistically. Originals are immutable
and hash-addressed; derived corruptions always point to their parent.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,random,urllib.request
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
CFG=ROOT/"config/public_evidence_sources.json"; OUT=ROOT/"data/public_trade_evidence"
FAULTS=["MISSING_INSTALLATION","MISSING_PRECURSOR","STALE_SUPPLIER_EVIDENCE","UNVERIFIED_EMISSIONS","MISSING_TARIC_DOCUMENT"]

def sha(b): return hashlib.sha256(b).hexdigest()
def write_json(p,o): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,indent=2,sort_keys=True)+"\n")
def acquire(cfg):
 out=[]
 for s in cfg["sources"]:
  if s["kind"] not in {"zip","xlsx","csv","json","xml"}: continue
  req=urllib.request.Request(s["url"],headers={"User-Agent":"EuroSetu-public-evidence-corpus/1"})
  with urllib.request.urlopen(req,timeout=60) as r: b=r.read()
  ext=s["kind"]; h=sha(b); p=OUT/"originals"/s["id"]/f"{h}.{ext}"
  p.parent.mkdir(parents=True,exist_ok=True)
  if not p.exists(): p.write_bytes(b)
  out.append({"source_id":s["id"],"path":str(p.relative_to(ROOT)),"sha256":h,"bytes":len(b),"retrieved_at":datetime.now(timezone.utc).isoformat()})
 return out
def synthetic():
 rng=random.Random(20261002); d=OUT/"evidence_room"; d.mkdir(parents=True,exist_ok=True)
 suppliers=[{"supplier_id":f"SUP-{i:03}","legal_name":f"Demo Steel Supplier {i:03}","country":"IN","installation_id":f"INST-{(i-1)%20+1:03}"} for i in range(1,51)]
 tx=[]; cns=["72083900","72085120","72107080","72191390","72254060"]; dest=["NL","DE","BE","FR","IT"]
 for i in range(100):
  fault=FAULTS[i%5] if i<25 else ""
  tx.append({"transaction_id":f"STEEL100-{i+1:03}","po_number":f"EU-PO-{1000+i}","supplier_id":suppliers[i%50]["supplier_id"],"cn_code":cns[i%5],"origin":"IN","destination":dest[i%5],"shipment_date":f"2026-{7+i%3:02}-15","quantity_t":round(rng.uniform(10,180),3),"line_value_eur":round(rng.uniform(25000,220000),2),"injected_fault":fault})
 for name,rows in [("suppliers.csv",suppliers),("transactions.csv",tx)]:
  p=d/name
  with p.open("w",newline="") as f:
   w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
 evidence=[]
 for i,t in enumerate(tx):
  for typ in ["COMMERCIAL_INVOICE","PACKING_LIST","MILL_TEST_CERTIFICATE","CBAM_INSTALLATION_DATA","ORIGIN_DECLARATION","TARIC_SUPPORTING_DOCUMENT"]:
   if (t["injected_fault"]=="MISSING_INSTALLATION" and typ=="CBAM_INSTALLATION_DATA") or (t["injected_fault"]=="MISSING_TARIC_DOCUMENT" and typ=="TARIC_SUPPORTING_DOCUMENT"): continue
   status="VALID"
   if t["injected_fault"]=="STALE_SUPPLIER_EVIDENCE" and typ=="CBAM_INSTALLATION_DATA":status="STALE"
   if t["injected_fault"]=="UNVERIFIED_EMISSIONS" and typ=="CBAM_INSTALLATION_DATA":status="UNVERIFIED"
   evidence.append({"evidence_id":f"EV-{i+1:03}-{typ}","transaction_id":t["transaction_id"],"type":typ,"status":status,"source_class":"SYNTHETIC","parent_artifact":"","content_hash":sha(f'{t["transaction_id"]}|{typ}|{status}'.encode())})
 write_json(d/"evidence.json",evidence)
 write_json(d/"fault_truth.json",{"faults":FAULTS,"blocked_transactions":[t["transaction_id"] for t in tx if t["injected_fault"]],"expected_initial":{"READY":75,"BLOCKED":25},"expected_after_remediation":{"READY":100,"BLOCKED":0}})
 return {"transactions":len(tx),"suppliers":len(suppliers),"evidence_objects":len(evidence),"faulted":25}
def manifest(cfg,acq,syn):
 files=[]
 for p in sorted((OUT/"evidence_room").glob("*")):
  if p.is_file(): files.append({"path":str(p.relative_to(ROOT)),"sha256":sha(p.read_bytes()),"bytes":p.stat().st_size,"source_class":"SYNTHETIC"})
 m={"schema_version":1,"generated_at":datetime.now(timezone.utc).isoformat(),"source_registry":cfg["sources"],"acquired_originals":acq,"synthetic_summary":syn,"artifacts":files,
 "claims_boundary":"Public/competitor sources define realistic inputs and workflow scenarios. Only direct authoritative expected outputs qualify as normative calculation oracles."}
 write_json(OUT/"manifest.json",m);return m
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--acquire",action="store_true");ap.add_argument("--clean",action="store_true");a=ap.parse_args()
 if a.clean and OUT.exists():
  import shutil;shutil.rmtree(OUT)
 cfg=json.loads(CFG.read_text());acq=acquire(cfg) if a.acquire else [];syn=synthetic();m=manifest(cfg,acq,syn)
 print(json.dumps({"manifest":str(OUT/"manifest.json"),"acquired":len(acq),**syn},indent=2))
if __name__=="__main__":main()
