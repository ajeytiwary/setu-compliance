from uuid import uuid4
from app.db import init_db,connect
from app.rules import STEEL_EU_RULES
from app.risk_drilldown import risk_drilldown
def _add(no,country,value,blocked):
 sid=str(uuid4()); now="2026-09-29T00:00:00+00:00"
 with connect() as c:
  c.execute("INSERT INTO shipments(id,shipment_no,exporter,facility,importer,destination_country,product,cn_code,tonnes,value_eur,emissions_method,supplier_required,supplier_complete,manual_hours,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(sid,no,"X","P","I",country,"HRC","7208",10,value,"actual",0,0,0,now,now))
  for r in STEEL_EU_RULES:
   status="MISSING" if r.code==blocked else "PASS"
   c.execute("INSERT INTO requirements(shipment_id,code,label,category,blocking,status,required_evidence,evidence_count) VALUES(?,?,?,?,?,?,?,0)",(sid,r.code,r.label,r.category,int(r.blocking),status,r.required_evidence))
 return sid
def test_drilldown_value_weighting_and_no_double_count():
 init_db(); a=_add("RISK-A","DE",200000,"CBAM"); _add("READY-B","NL",100000,None)
 with connect() as c:
  c.execute("UPDATE requirements SET status='MISSING' WHERE shipment_id=? AND code='CUSTOMS'",(a,))
 d=risk_drilldown(); assert d["metrics"]["revenue_at_risk_eur"]>=200000
 target=[x for x in d["drilldown"] if x["shipment_no"]=="RISK-A"]; assert {x["blocker"]["code"] for x in target}=={"CBAM","CUSTOMS"}
 de=next(x for x in d["countries"] if x["country"]=="DE"); assert de["at_risk_value_eur"]>=200000
