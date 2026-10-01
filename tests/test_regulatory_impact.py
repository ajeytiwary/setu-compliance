from uuid import uuid4
from app.db import connect,init_db
from app.regulatory_impact import record_change,queue

def _shipment():
 init_db();sid=str(uuid4());now="2026-10-01T00:00:00+00:00"
 with connect() as c:
  c.execute("INSERT INTO shipments(id,shipment_no,exporter,facility,importer,destination_country,product,cn_code,tonnes,value_eur,emissions_method,supplier_required,supplier_complete,manual_hours,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
   (sid,"IMPACT-"+sid[:6],"Exporter","Plant","Importer","NL","HRC","72083900",10,100000,"actual",0,0,0,now,now))
 return sid

def test_source_hash_change_queues_affected_shipments():
 sid=_shipment();out=record_change("taric_measures","old","new")
 assert out["changed"] is True and out["queued"]==1
 q=queue("REVIEW_REQUIRED");assert len(q)==1 and q[0]["shipment_id"]==sid
 assert "TARIC_CLASSIFICATION" in q[0]["rule_codes"]

def test_same_hash_is_idempotent():
 _shipment();assert record_change("eucdm","same","same")=={"changed":False,"queued":0}
 assert queue()==[]
