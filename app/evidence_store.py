from __future__ import annotations
import hashlib,json,os
from pathlib import Path
ROOT=Path(os.getenv("EVIDENCE_ROOT","data/evidence"))
def put(tenant_id,shipment_ref,filename,content,metadata=None):
 if not tenant_id or not shipment_ref: raise ValueError("tenant and shipment required")
 digest=hashlib.sha256(content).hexdigest(); folder=ROOT/tenant_id/shipment_ref/digest; folder.mkdir(parents=True,exist_ok=True)
 blob=folder/"payload"; meta=folder/"metadata.json"
 if blob.exists() and blob.read_bytes()!=content: raise RuntimeError("integrity failure")
 if not blob.exists(): blob.write_bytes(content)
 record={"sha256":digest,"filename":filename,"tenant_id":tenant_id,"shipment_ref":shipment_ref,**(metadata or {})}
 if not meta.exists(): meta.write_text(json.dumps(record,sort_keys=True,indent=2))
 return record
def verify(tenant_id,shipment_ref,digest):
 p=ROOT/tenant_id/shipment_ref/digest/"payload"
 return p.exists() and hashlib.sha256(p.read_bytes()).hexdigest()==digest
