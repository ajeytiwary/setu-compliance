from uuid import uuid4
from app.db import init_db,connect
from app.rules import STEEL_EU_RULES
from app.risk_drilldown import risk_drilldown,simulate_remediation
def _add(no,country,value,blocked=None):
 sid=str(uuid4()); now="2026-09-29T00:00:00+00:00"
 with connect() as c:
  c.execute("INSERT INTO shipments(id,shipment_no,exporter,facility,importer,destination_country,product,cn_code,tonnes,value_eur,emissions_method,supplier_required,supplier_complete,manual_hours,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(sid,no+"-"+sid[:6],"X","P","I",country,"HRC","7208",10,value,"actual",0,0,0,now,now))
  for r in STEEL_EU_RULES:
   status="MISSING" if r.code==blocked else "PASS"
   c.execute("INSERT INTO requirements(shipment_id,code,label,category,blocking,status,required_evidence,evidence_count) VALUES(?,?,?,?,?,?,?,0)",(sid,r.code,r.label,r.category,int(r.blocking),status,r.required_evidence))
 return sid
def test_drilldown_value_weighting_and_no_double_count():
 init_db(); a=_add("RISK-A","DE",200000,"GENEALOGY"); _add("READY-B","NL",100000)
 with connect() as c:c.execute("UPDATE requirements SET status='MISSING' WHERE shipment_id=? AND code='CBAM_ACTIVITY'",(a,))
 d=risk_drilldown(); target=[x for x in d["drilldown"] if x["shipment_id"]==a]
 assert {x["blocker"]["code"] for x in target}=={"GENEALOGY","CBAM_ACTIVITY"}
 de=next(x for x in d["countries"] if x["country"]=="DE"); assert de["at_risk_value_eur"]>=200000
def test_simulation_unlocks_only_when_last_blocker_is_fixed():
 init_db(); sid=_add("SIM-A","FR",500000,"GENEALOGY")
 one=simulate_remediation(sid,"GENEALOGY",5000); assert one["after"]["market_ready"] is True; assert one["after"]["revenue_unlocked_eur"]==500000; assert one["after"]["net_value_unlocked_eur"]==495000
 with connect() as c:c.execute("UPDATE requirements SET status='MISSING' WHERE shipment_id=? AND code='CBAM_ACTIVITY'",(sid,))
 two=simulate_remediation(sid,"GENEALOGY",5000); assert two["after"]["market_ready"] is False; assert two["after"]["revenue_unlocked_eur"]==0; assert two["after"]["next_blocker"]["code"]=="CBAM_ACTIVITY"
 with connect() as c:
  status=c.execute("SELECT status FROM requirements WHERE shipment_id=? AND code='GENEALOGY'",(sid,)).fetchone()[0]
 assert status=="MISSING"
