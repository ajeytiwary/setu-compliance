from __future__ import annotations
from datetime import datetime,timezone
from uuid import uuid4
from .db import connect,rows

DATASET_RULES={
 "taric_measures":["TARIC_CLASSIFICATION","CUSTOMS_DUTY"],
 "eucdm":["CUSTOMS_DECLARATION"],
 "eu_sanctions":["SANCTIONS"],
 "echa_candidate_list":["REACH_SVHC"],
 "scip_schema":["SCIP"],
 "cbam_defaults":["CBAM_EMISSIONS"],
 "cbam_benchmarks":["CBAM_EMISSIONS"],
 "steel_2026_1457":["STEEL_QUOTA"],
}
def record_change(dataset:str,old_sha:str|None,new_sha:str|None)->dict:
 if not new_sha or old_sha==new_sha:return {"changed":False,"queued":0}
 codes=DATASET_RULES.get(dataset,[])
 now=datetime.now(timezone.utc).isoformat();queued=0
 with connect() as c:
  shipments=rows(c,"SELECT id,shipment_no,cn_code,destination_country FROM shipments")
  for s in shipments:
   c.execute("INSERT INTO regulatory_change_impacts(id,dataset,old_sha,new_sha,shipment_id,shipment_no,rule_codes,status,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
    (str(uuid4()),dataset,old_sha,new_sha,s["id"],s["shipment_no"],",".join(codes),"REVIEW_REQUIRED",now));queued+=1
 return {"changed":True,"queued":queued,"dataset":dataset,"rule_codes":codes}
def queue(status:str|None=None)->list[dict]:
 with connect() as c:
  if status:return rows(c,"SELECT * FROM regulatory_change_impacts WHERE status=? ORDER BY created_at DESC",(status,))
  return rows(c,"SELECT * FROM regulatory_change_impacts ORDER BY created_at DESC")
