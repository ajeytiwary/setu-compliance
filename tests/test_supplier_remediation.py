from uuid import uuid4
import pytest
from app.db import init_db,connect,row
from app.evidence_network import create_supplier,link_supplier,add_supplier_evidence,create_request,resolve_request,remediation_summary
from app.rules import STEEL_EU_RULES
def _shipment():
 init_db(); sid=str(uuid4()); no="TEST-"+sid[:8]; now="2026-09-29T00:00:00+00:00"
 with connect() as c:
  c.execute("INSERT INTO shipments(id,shipment_no,exporter,facility,importer,destination_country,product,cn_code,tonnes,value_eur,emissions_method,supplier_required,supplier_complete,manual_hours,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(sid,no,"Exporter","Plant","Importer","DE","HRC","7208",10,100000,"actual",0,0,0,now,now))
  for r in STEEL_EU_RULES:c.execute("INSERT INTO requirements(shipment_id,code,label,category,blocking,status,required_evidence,evidence_count) VALUES(?,?,?,?,?,?,?,0)",(sid,r.code,r.label,r.category,int(r.blocking),"MISSING",r.required_evidence))
 return sid
def test_verified_supplier_evidence_resolves_blocker():
 sid=_shipment(); s=create_supplier("Test supplier"); link_supplier(s["id"],sid,"ferroalloy",1,"CBAM_PRECURSOR")
 with connect() as c:assert row(c,"SELECT status FROM requirements WHERE shipment_id=? AND code='SUPPLIER_DATA'",(sid,))["status"]=="MISSING"
 req=create_request(sid,s["id"],"SUPPLIER_DATA","CBAM_PRECURSOR","Procurement","2026-10-01")
 pending=add_supplier_evidence(s["id"],"CBAM_PRECURSOR","pending-file","PENDING")
 with pytest.raises(ValueError):resolve_request(req["id"],pending["id"])
 verified=add_supplier_evidence(s["id"],"CBAM_PRECURSOR","verified-file","VERIFIED",verifier="Accredited verifier")
 resolved=resolve_request(req["id"],verified["id"]); assert resolved["status"]=="RESOLVED"
 with connect() as c:
  sh=row(c,"SELECT supplier_required,supplier_complete FROM shipments WHERE id=?",(sid,)); rr=row(c,"SELECT status FROM requirements WHERE shipment_id=? AND code='SUPPLIER_DATA'",(sid,))
 assert sh["supplier_required"]==1 and sh["supplier_complete"]==1; assert rr["status"]=="PASS"
def test_remediation_summary_deduplicates_revenue_at_risk():
 sid=_shipment(); s=create_supplier("Risk supplier"); link_supplier(s["id"],sid,"a",1,"PCF")
 create_request(sid,s["id"],"SUPPLIER_DATA","PCF","Buyer"); create_request(sid,s["id"],"SUPPLIER_DATA","CERT","Buyer")
 summary=remediation_summary(); assert summary["open_requests"]>=2; assert summary["revenue_at_risk_eur"]>=100000
