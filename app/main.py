from __future__ import annotations
import hashlib,io,json,zipfile
from datetime import datetime,timezone
from pathlib import Path
from uuid import uuid4
from fastapi import FastAPI,HTTPException,Response
from fastapi.responses import FileResponse,HTMLResponse
from pydantic import BaseModel,Field
from .db import init_db,connect,rows,row,audit
from .metrics import shipment_score,portfolio_metrics
from .rules import STEEL_EU_RULES,initial_status
from .seed import seed_if_empty
app=FastAPI(title="Setu EU Market Access OS",version="0.2.0")
STATIC=Path(__file__).parent/"static"
class ShipmentIn(BaseModel):
 shipment_no:str; exporter:str="Indian steel exporter"; facility:str; importer:str; destination_country:str; product:str="Hot Rolled Coil"; cn_code:str="7208"; tonnes:float=Field(gt=0); value_eur:float=Field(gt=0); emissions_method:str="actual"; embedded_emissions_tco2e_per_t:float|None=None; supplier_required:int=0; supplier_complete:int=0; manual_hours:float=0
class EvidenceIn(BaseModel):
 requirement_code:str; filename:str; evidence_type:str; issuer:str|None=None; content:str="demo evidence"; valid_until:str|None=None
class VerificationIn(BaseModel):
 verifier:str; status:str=Field(pattern="^(IN_REVIEW|VERIFIED|REJECTED)$"); started_at:str|None=None; completed_at:str|None=None; finding_count:int=0; report_ref:str|None=None
class IntegrationImportIn(BaseModel):csv_content:str; source_name:str="api"
class CBAMCalculationIn(BaseModel):payload:dict
class OriginEvaluationIn(BaseModel):payload:dict
class PipelineOriginIn(BaseModel):product_specific_rule:dict|None=None
class SupplierIn(BaseModel):name:str; facility:str|None=None; country:str="IN"; supplier_id:str|None=None
class SupplierLinkIn(BaseModel):shipment_id:str; material:str|None=None; quantity_t:float|None=None; required_evidence_type:str|None=None
class SupplierEvidenceIn(BaseModel):evidence_type:str; content:str; status:str=Field(pattern="^(PENDING|VERIFIED|REJECTED)$"); issuer:str|None=None; verifier:str|None=None; valid_until:str|None=None; source_ref:str|None=None; metadata:dict|None=None
class EvidenceRequestIn(BaseModel):shipment_id:str; supplier_id:str; requirement_code:str="SUPPLIER_DATA"; evidence_type:str; owner:str; due_date:str|None=None; message:str|None=None
class EvidenceResolveIn(BaseModel):evidence_id:str
@app.on_event("startup")
def startup():init_db();seed_if_empty()
def detailed(conn,s):
 req=rows(conn,"SELECT * FROM requirements WHERE shipment_id=? ORDER BY blocking DESC,category,code",(s["id"],)); ver=row(conn,"SELECT * FROM verifications WHERE shipment_id=? ORDER BY started_at DESC LIMIT 1",(s["id"],)); cycle=None
 if ver and ver.get("completed_at"):cycle=(datetime.fromisoformat(ver["completed_at"])-datetime.fromisoformat(ver["started_at"])).total_seconds()/86400
 return {**s,"requirements":req,"public_sources":rows(conn,"SELECT * FROM public_sources WHERE shipment_id=? ORDER BY id",(s["id"],)),"verification":ver,"verification_cycle_days":round(cycle,1) if cycle is not None else None,"score":shipment_score(s,req,ver)}
@app.get("/",response_class=HTMLResponse)
def home():
 p=STATIC/"index.html"
 return FileResponse(p) if p.exists() else HTMLResponse("<h1>Setu Compliance</h1><p>Open <a href='/docs'>/docs</a> for the API.</p>")
@app.get("/app.js")
def js():return FileResponse(STATIC/"app.js",media_type="application/javascript")
@app.get("/styles.css")
def css():return FileResponse(STATIC/"styles.css",media_type="text/css")
@app.get("/api/dashboard")
def dashboard():
 with connect() as conn:
  ds=[detailed(conn,s) for s in rows(conn,"SELECT * FROM shipments ORDER BY created_at DESC")]
  return {"metrics":portfolio_metrics(ds),"shipments":ds,"case_study":True,"metric_definition":"Production metric: compliant EU-bound shipment value / total EU-bound shipment value. Public records do not disclose shipment-level value, so the public case does not fabricate this KPI."}
@app.get("/api/shipments/{shipment_id}")
def shipment(shipment_id):
 with connect() as conn:
  s=row(conn,"SELECT * FROM shipments WHERE id=? OR shipment_no=?",(shipment_id,shipment_id))
  if not s:raise HTTPException(404,"shipment not found")
  return detailed(conn,s)
@app.post("/api/shipments",status_code=201)
def create_shipment(x:ShipmentIn):
 sid=str(uuid4()); now=datetime.now(timezone.utc).isoformat(); d=x.model_dump()
 with connect() as conn:
  conn.execute("INSERT INTO shipments(id,shipment_no,exporter,facility,importer,destination_country,product,cn_code,tonnes,value_eur,emissions_method,embedded_emissions_tco2e_per_t,supplier_required,supplier_complete,manual_hours,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(sid,d["shipment_no"],d["exporter"],d["facility"],d["importer"],d["destination_country"],d["product"],d["cn_code"],d["tonnes"],d["value_eur"],d["emissions_method"],d["embedded_emissions_tco2e_per_t"],d["supplier_required"],d["supplier_complete"],d["manual_hours"],now,now))
  for r in STEEL_EU_RULES:conn.execute("INSERT INTO requirements(shipment_id,code,label,category,blocking,status,required_evidence,evidence_count) VALUES(?,?,?,?,?,?,?,0)",(sid,r.code,r.label,r.category,int(r.blocking),initial_status(r,d),r.required_evidence))
  audit(conn,sid,"shipment.created",d); return detailed(conn,row(conn,"SELECT * FROM shipments WHERE id=?",(sid,)))
@app.post("/api/shipments/{shipment_id}/evidence",status_code=201)
def add_evidence(shipment_id,x:EvidenceIn):
 eid=str(uuid4()); sha=hashlib.sha256(x.content.encode()).hexdigest()
 with connect() as conn:
  req=row(conn,"SELECT * FROM requirements WHERE shipment_id=? AND code=?",(shipment_id,x.requirement_code))
  if not req:raise HTTPException(404,"requirement not found")
  conn.execute("INSERT INTO evidence(id,shipment_id,requirement_code,filename,evidence_type,issuer,sha256,valid_until,created_at) VALUES(?,?,?,?,?,?,?,?,?)",(eid,shipment_id,x.requirement_code,x.filename,x.evidence_type,x.issuer,sha,x.valid_until,datetime.now(timezone.utc).isoformat()))
  count=conn.execute("SELECT COUNT(*) FROM evidence WHERE shipment_id=? AND requirement_code=?",(shipment_id,x.requirement_code)).fetchone()[0]; conn.execute("UPDATE requirements SET evidence_count=? WHERE shipment_id=? AND code=?",(count,shipment_id,x.requirement_code))
  if count>=req["required_evidence"] and x.requirement_code not in ("CBAM_VERIFICATION","SUPPLIER_DATA","CBAM_EMISSIONS"):conn.execute("UPDATE requirements SET status='PASS' WHERE shipment_id=? AND code=?",(shipment_id,x.requirement_code))
  audit(conn,shipment_id,"evidence.added",{"id":eid,"requirement":x.requirement_code,"sha256":sha}); return {"id":eid,"sha256":sha,"evidence_count":count}
@app.get("/api/shipments/{shipment_id}/dpp")
def dpp(shipment_id):
 with connect() as conn:
  s=row(conn,"SELECT * FROM shipments WHERE id=?",(shipment_id,))
  if not s:raise HTTPException(404,"shipment not found")
  d=detailed(conn,s); return {"@context":["https://schema.org/"],"passport":{"id":f"urn:setu:dpp:{s['id']}","status":"MVP_READINESS","schemaVersion":"steel-v0.1"},"product":{"uniqueProductIdentifier":s["shipment_no"],"name":s["product"],"commodityCode":s["cn_code"],"manufacturer":s["exporter"],"facility":s["facility"],"massTonnes":s["tonnes"]},"environment":{"embeddedEmissions":{"value":s["embedded_emissions_tco2e_per_t"],"unit":"tCO2e/t"}},"compliance":{"autoReady":d["score"]["auto_ready"],"readinessScore":d["score"]["readiness_score"],"blockers":d["score"]["blockers"]},"notice":"MVP readiness payload; final steel ESPR fields remain versioned/configurable."}
@app.get("/api/market-access/order-book")
def market_access_order_book():
 from .market_access import order_book
 return order_book()
@app.get("/api/market-access/risk-drilldown")
def market_access_risk_drilldown():
 from .risk_drilldown import risk_drilldown
 return risk_drilldown()
@app.get("/api/evidence-graph")
def evidence_graph():
 with connect() as conn:
  evidence=rows(conn,"SELECT e.*,s.name supplier_name FROM supplier_evidence e JOIN suppliers s ON s.id=e.supplier_id ORDER BY e.created_at DESC")
  requests=rows(conn,"SELECT id,shipment_id,supplier_id,requirement_code,evidence_type,status,submitted_evidence_id FROM evidence_requests ORDER BY created_at DESC")
 return {"supplier_evidence":evidence,"requests":requests,"model":"shipment requirement → supplier → evidence request → verified evidence → readiness"}
@app.get("/api/suppliers")
def suppliers():
 from .evidence_network import list_suppliers
 return {"suppliers":list_suppliers(),"principle":"verify once, permission-share many"}
@app.post("/api/suppliers",status_code=201)
def supplier_create(x:SupplierIn):
 from .evidence_network import create_supplier
 return create_supplier(**x.model_dump())
@app.get("/api/suppliers/{supplier_id}")
def supplier_detail(supplier_id):
 from .evidence_network import get_supplier
 out=get_supplier(supplier_id)
 if not out:raise HTTPException(404,"supplier not found")
 return out
@app.post("/api/suppliers/{supplier_id}/link",status_code=201)
def supplier_link(supplier_id,x:SupplierLinkIn):
 from .evidence_network import link_supplier
 try:return link_supplier(supplier_id,**x.model_dump())
 except ValueError as e:raise HTTPException(422,str(e))
@app.post("/api/suppliers/{supplier_id}/evidence",status_code=201)
def supplier_evidence(supplier_id,x:SupplierEvidenceIn):
 from .evidence_network import add_supplier_evidence
 try:return add_supplier_evidence(supplier_id,**x.model_dump())
 except ValueError as e:raise HTTPException(422,str(e))
@app.get("/api/remediation")
def remediation():
 from .evidence_network import remediation_summary
 return remediation_summary()
@app.post("/api/remediation/requests",status_code=201)
def remediation_create(x:EvidenceRequestIn):
 from .evidence_network import create_request
 try:return create_request(**x.model_dump())
 except ValueError as e:raise HTTPException(422,str(e))
@app.post("/api/remediation/requests/{request_id}/resolve")
def remediation_resolve(request_id,x:EvidenceResolveIn):
 from .evidence_network import resolve_request
 try:return resolve_request(request_id,x.evidence_id)
 except ValueError as e:raise HTTPException(422,str(e))
@app.get("/api/integrations")
def integrations_catalog():
 from .integrations import integration_catalog
 return integration_catalog()
@app.post("/api/integrations/{connector}/import")
def integrations_import(connector,x:IntegrationImportIn):
 from .integrations import import_csv,CONNECTORS
 if connector not in CONNECTORS:raise HTTPException(404,"unknown connector")
 try:return import_csv(connector,x.csv_content,x.source_name)
 except ValueError as e:raise HTTPException(422,str(e))
@app.post("/api/integrations/{connector}/import-sample")
def integrations_import_sample(connector):
 from .integrations import import_sample,CONNECTORS
 if connector not in CONNECTORS:raise HTTPException(404,"unknown connector")
 try:return import_sample(connector)
 except ValueError as e:raise HTTPException(422,str(e))
@app.get("/api/integrations/canonical/summary")
def canonical_summary():
 from .integrations import canonical_summary
 return canonical_summary()
@app.get("/api/cbam/methodologies")
def cbam_methodologies():
 from .cbam_engine import METHODOLOGIES
 return {"methodologies":list(METHODOLOGIES.values())}
@app.post("/api/cbam/calculate")
def cbam_calculate(x:CBAMCalculationIn):
 from .cbam_engine import persist_calculation
 try:return persist_calculation(x.payload)
 except ValueError as e:raise HTTPException(422,str(e))
@app.get("/api/cbam/calculations")
def cbam_calculations():
 from .cbam_engine import list_calculations
 return {"calculations":list_calculations()}
@app.get("/api/fta/agreements")
def fta_agreements():
 from .fta_origin import AGREEMENTS
 return {"agreements":list(AGREEMENTS.values()),"current_as_of":"2026-08-28"}
@app.post("/api/fta/origin/evaluate")
def fta_origin_evaluate(x:OriginEvaluationIn):
 from .fta_origin import persist_origin_evaluation
 try:return persist_origin_evaluation(x.payload)
 except ValueError as e:raise HTTPException(422,str(e))
@app.get("/api/live-connections")
def live_connections():
 from .live_connectors import connection_status
 return {"connections":connection_status(),"note":"Private SAP/MES/EMS connections require customer endpoints and credentials."}
@app.post("/api/live-connections/sap/{connector}/sync")
def live_sap(connector):
 from .live_connectors import sap_odata_pull
 if connector not in ("sap_sd","sap_mm"):raise HTTPException(404,"connector must be sap_sd or sap_mm")
 try:return sap_odata_pull(connector)
 except Exception as e:raise HTTPException(502,str(e))
@app.post("/api/live-connections/mes/sync")
def live_mes():
 from .live_connectors import generic_mes_pull
 try:return generic_mes_pull()
 except Exception as e:raise HTTPException(502,str(e))
@app.post("/api/live-connections/ems/sync")
def live_ems():
 from .live_connectors import generic_ems_pull
 try:return generic_ems_pull()
 except Exception as e:raise HTTPException(502,str(e))
@app.post("/api/pipeline/steel/{shipment_ref}/cbam")
def pipeline_cbam(shipment_ref):
 from .steel_pipeline import evaluate_shipment_cbam
 try:return evaluate_shipment_cbam(shipment_ref)
 except ValueError as e:raise HTTPException(422,str(e))
@app.post("/api/pipeline/steel/{shipment_ref}/origin")
def pipeline_origin(shipment_ref,x:PipelineOriginIn):
 from .steel_pipeline import evaluate_shipment_origin
 try:return evaluate_shipment_origin(shipment_ref,x.product_specific_rule)
 except ValueError as e:raise HTTPException(422,str(e))
