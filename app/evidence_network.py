from __future__ import annotations
import hashlib,json
from datetime import datetime,timezone
from uuid import uuid4
from .db import connect,rows,row,audit
def _now():return datetime.now(timezone.utc).isoformat()
def create_supplier(name,facility=None,country="IN",supplier_id=None):
 sid=supplier_id or str(uuid4()); now=_now()
 with connect() as conn:
  conn.execute("INSERT INTO suppliers(id,name,facility,country,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",(sid,name,facility,country,"ACTIVE",now,now))
 return get_supplier(sid)
def get_supplier(supplier_id):
 with connect() as conn:
  s=row(conn,"SELECT * FROM suppliers WHERE id=?",(supplier_id,))
  if not s:return None
  s["evidence"]=rows(conn,"SELECT * FROM supplier_evidence WHERE supplier_id=? ORDER BY created_at DESC",(supplier_id,))
  s["shipments"]=rows(conn,"SELECT l.*,sh.shipment_no,sh.product,sh.value_eur FROM supplier_shipment_links l JOIN shipments sh ON sh.id=l.shipment_id WHERE l.supplier_id=?",(supplier_id,))
  return s
def list_suppliers():
 with connect() as conn:
  out=rows(conn,"SELECT s.*,COUNT(DISTINCT l.shipment_id) shipment_count,COUNT(DISTINCT CASE WHEN e.status='VERIFIED' THEN e.id END) verified_evidence_count FROM suppliers s LEFT JOIN supplier_shipment_links l ON l.supplier_id=s.id LEFT JOIN supplier_evidence e ON e.supplier_id=s.id GROUP BY s.id ORDER BY s.name")
 return out
def _resolve_shipment(conn,ref):
 s=row(conn,"SELECT * FROM shipments WHERE id=? OR shipment_no=?",(ref,ref))
 if not s:raise ValueError("shipment not found")
 return s["id"]
def link_supplier(supplier_id,shipment_id,material=None,quantity_t=None,required_evidence_type=None):
 lid=str(uuid4())
 with connect() as conn:
  if not row(conn,"SELECT id FROM suppliers WHERE id=?",(supplier_id,)):raise ValueError("supplier not found")
  shipment_id=_resolve_shipment(conn,shipment_id)
  conn.execute("INSERT OR IGNORE INTO supplier_shipment_links(id,supplier_id,shipment_id,material,quantity_t,required_evidence_type,created_at) VALUES(?,?,?,?,?,?,?)",(lid,supplier_id,shipment_id,material,quantity_t,required_evidence_type,_now()))
  _refresh_supplier_requirement(conn,shipment_id); audit(conn,shipment_id,"supplier.linked",{"supplier_id":supplier_id,"material":material})
 return {"id":lid,"supplier_id":supplier_id,"shipment_id":shipment_id}
def add_supplier_evidence(supplier_id,evidence_type,content,status="PENDING",issuer=None,verifier=None,valid_until=None,source_ref=None,metadata=None):
 eid=str(uuid4()); now=_now(); digest=hashlib.sha256(content.encode()).hexdigest()
 with connect() as conn:
  if not row(conn,"SELECT id FROM suppliers WHERE id=?",(supplier_id,)):raise ValueError("supplier not found")
  conn.execute("INSERT INTO supplier_evidence(id,supplier_id,evidence_type,status,issuer,verifier,valid_until,sha256,source_ref,metadata_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(eid,supplier_id,evidence_type,status,issuer,verifier,valid_until,digest,source_ref,json.dumps(metadata or {}),now,now))
  linked=rows(conn,"SELECT shipment_id FROM supplier_shipment_links WHERE supplier_id=?",(supplier_id,))
  for x in linked:_refresh_supplier_requirement(conn,x["shipment_id"])
 return {"id":eid,"supplier_id":supplier_id,"evidence_type":evidence_type,"status":status,"sha256":digest}
def create_request(shipment_id,supplier_id,requirement_code,evidence_type,owner,due_date=None,message=None):
 rid=str(uuid4()); now=_now()
 with connect() as conn:
  shipment_id=_resolve_shipment(conn,shipment_id)
  if not row(conn,"SELECT id FROM suppliers WHERE id=?",(supplier_id,)):raise ValueError("supplier not found")
  conn.execute("INSERT INTO evidence_requests(id,shipment_id,supplier_id,requirement_code,evidence_type,owner,due_date,status,message,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(rid,shipment_id,supplier_id,requirement_code,evidence_type,owner,due_date,"OPEN",message,now,now))
  audit(conn,shipment_id,"supplier_evidence.requested",{"request_id":rid,"supplier_id":supplier_id,"evidence_type":evidence_type,"owner":owner,"due_date":due_date})
 return get_request(rid)
def get_request(request_id):
 with connect() as conn:return row(conn,"SELECT r.*,s.name supplier_name,sh.shipment_no FROM evidence_requests r JOIN suppliers s ON s.id=r.supplier_id JOIN shipments sh ON sh.id=r.shipment_id WHERE r.id=?",(request_id,))
def list_requests(status=None):
 with connect() as conn:
  q="SELECT r.*,s.name supplier_name,sh.shipment_no,sh.value_eur FROM evidence_requests r JOIN suppliers s ON s.id=r.supplier_id JOIN shipments sh ON sh.id=r.shipment_id"; p=()
  if status:q+=" WHERE r.status=?";p=(status,)
  return rows(conn,q+" ORDER BY COALESCE(r.due_date,'9999-12-31'),r.created_at",p)
def resolve_request(request_id,evidence_id):
 now=_now()
 with connect() as conn:
  req=row(conn,"SELECT * FROM evidence_requests WHERE id=?",(request_id,)); ev=row(conn,"SELECT * FROM supplier_evidence WHERE id=?",(evidence_id,))
  if not req:raise ValueError("request not found")
  if not ev or ev["supplier_id"]!=req["supplier_id"]:raise ValueError("evidence does not belong to request supplier")
  if ev["status"]!="VERIFIED":raise ValueError("evidence must be VERIFIED before it can resolve a request")
  conn.execute("UPDATE evidence_requests SET status='RESOLVED',submitted_evidence_id=?,resolved_at=?,updated_at=? WHERE id=?",(evidence_id,now,now,request_id))
  _refresh_supplier_requirement(conn,req["shipment_id"]); audit(conn,req["shipment_id"],"supplier_evidence.resolved",{"request_id":request_id,"evidence_id":evidence_id})
 return get_request(request_id)
def _refresh_supplier_requirement(conn,shipment_id):
 links=rows(conn,"SELECT * FROM supplier_shipment_links WHERE shipment_id=?",(shipment_id,)); required=[x for x in links if x.get("required_evidence_type")]
 complete=0
 for x in required:
  ok=row(conn,"SELECT id FROM supplier_evidence WHERE supplier_id=? AND evidence_type=? AND status='VERIFIED' AND (valid_until IS NULL OR valid_until>=date('now')) LIMIT 1",(x["supplier_id"],x["required_evidence_type"]))
  complete+=1 if ok else 0
 conn.execute("UPDATE shipments SET supplier_required=?,supplier_complete=?,updated_at=? WHERE id=?",(len(required),complete,_now(),shipment_id))
 if required:conn.execute("UPDATE requirements SET status=?,notes=? WHERE shipment_id=? AND code='SUPPLIER_DATA'",("PASS" if complete==len(required) else "MISSING",f"{complete}/{len(required)} required supplier evidence links verified",shipment_id))
def remediation_summary():
 reqs=list_requests(); open_reqs=[r for r in reqs if r["status"]=="OPEN"]
 return {"open_requests":len(open_reqs),"resolved_requests":sum(1 for r in reqs if r["status"]=="RESOLVED"),"revenue_at_risk_eur":sum({r["shipment_id"]:r["value_eur"] for r in open_reqs}.values()),"requests":reqs}
