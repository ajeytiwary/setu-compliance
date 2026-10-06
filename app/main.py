from __future__ import annotations
import hashlib,io,json,os,re,secrets,sqlite3,zipfile
from datetime import datetime,timezone
from pathlib import Path
from uuid import uuid4
from fastapi import FastAPI,HTTPException,Request,Response
from fastapi.responses import FileResponse,HTMLResponse,RedirectResponse
from pydantic import BaseModel,Field
from .db import init_db,connect,rows,row,audit
from .metrics import shipment_score,portfolio_metrics
from .rules import STEEL_EU_RULES,initial_status
from .seed import seed_if_empty
from .v1_api import router as v1_router, internal as internal_router
app=FastAPI(title="EuroSetu EU Market Access OS",version="0.2.0")
app.include_router(v1_router)
app.include_router(internal_router)
STATIC=Path(__file__).parent/"static"
PUBLIC_PAGE_PATHS={"/trust","/benchmarks","/product","/workflow","/pricing","/brokers","/liability-preview","/threshold-checker","/carbon-price-relief","/cbam-rate","/guides","/worked-example","/supplier-data-template","/security","/privacy","/dpa","/terms","/faq","/sectors","/account","/changelog"}
# The legacy demo API stores records without tenant keys. Expose only the
# tenant-scoped dossier workflow and stateless/public endpoints in production.
@app.middleware("http")
async def production_api_boundary(request:Request,call_next):
 if os.getenv("EUROSETU_ENV")=="production" and os.getenv("EUROSETU_SPLIT_HOSTS")=="1":
  host=request.headers.get("host","").split(":",1)[0].lower().rstrip(".")
  expected=os.getenv("EUROSETU_APP_HOST","app.eurosetu.trade").lower().rstrip(".")
  if host!=expected:return Response(status_code=421,content="Wrong application host")
  path=request.url.path
  if path in PUBLIC_PAGE_PATHS or path.startswith("/guides/") or path in {"/benchmarks.js","/robots.txt","/sitemap.xml"}:return Response(status_code=404)
  if path in {"/api/leads","/api/leads/verify"}:return Response(status_code=404)
  if path.startswith("/api/tools/") or path=="/api/contact":
   proxy_secret=os.getenv("EUROSETU_PUBLIC_PROXY_SECRET","")
   given=request.headers.get("x-eurosetu-public-proxy-secret","")
   if not proxy_secret:return Response(status_code=503,content="Public proxy unconfigured")
   if not secrets.compare_digest(given,proxy_secret):return Response(status_code=403)
 if os.getenv("EUROSETU_ENV")=="production" and request.url.path.startswith(("/v1/","/internal/")):
  return Response(status_code=404)
 if os.getenv("EUROSETU_ENV")=="production" and request.url.path=="/admin" and os.getenv("EUROSETU_SPLIT_HOSTS")!="1":return Response(status_code=404)
 if os.getenv("EUROSETU_ENV")=="production" and request.url.path.startswith("/api/"):
  path=request.url.path
  allowed=(path.startswith("/api/real-dossiers") or
           path == "/api/commercial/readiness" or
           path == "/api/admin/revoke-principal" or
           (os.getenv("EUROSETU_SPLIT_HOSTS")=="1" and path in ("/api/admin/requests","/api/admin/mint")) or
           path.startswith("/api/benchmarks/releases") or
           path.startswith("/api/tools/") or
           path in ("/api/leads","/api/leads/verify","/api/contact"))
  if not allowed:return Response(status_code=404)
  if (os.getenv("EUROSETU_RECURRING_SAAS_ENABLED")=="1"
      and path.startswith("/api/real-dossiers")
      and request.method in {"POST","PUT","PATCH","DELETE"}):
   from .commercial_gate import assess
   try:
    if not assess(os.environ["EUROSETU_DEPLOYMENT_TENANT"],quick=True)["ready_for_recurring_saas"]:
     return Response(status_code=503,content="Commercial release gate closed")
   except Exception:
    return Response(status_code=503,content="Commercial release gate closed")
 return await call_next(request)
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
class SupplierEvidenceSubmitIn(BaseModel):evidence_type:str; content:str; issuer:str|None=None; source_ref:str|None=None
class SupplierEvidenceVerifyIn(BaseModel):verifier:str
class RemediationSimulationIn(BaseModel):requirement_code:str; estimated_cost_eur:float=Field(default=0,ge=0)
class ActiveEntitlementIn(BaseModel):payload:dict
class CBAMVerificationReportIn(BaseModel):payload:dict
class PublicDataImportIn(BaseModel):csv_content:str; as_of:str|None=None
class PublicDataSyncIn(BaseModel):url:str; as_of:str|None=None
class TaricResolveIn(BaseModel):payload:dict
class RegulatoryPayloadIn(BaseModel):payload:dict
class ReferenceCSVIn(BaseModel):csv_content:str
class LeadIn(BaseModel):
 name:str; work_email:str; company:str; role:str|None=None; message:str|None=None
class ContactIn(BaseModel):
 name:str; work_email:str; company:str|None=None; topic:str="General enquiry"; message:str|None=None; website:str|None=None
EMAIL_RE=re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
def _notify_founder(payload:dict):
 # Fire-and-forget: site button -> Worker /notify -> email FROM request@.
 # Never blocks the signup; failures only audit-log.
 import urllib.request
 url=(os.getenv("EUROSETU_NOTIFY_URL") or "").strip()
 if not url:return
 body=dict(payload); secret=(os.getenv("EUROSETU_NOTIFY_SECRET") or "").strip()
 if secret:body["secret"]=secret
 try:req=urllib.request.Request(url,data=json.dumps(body).encode(),headers={"Content-Type":"application/json","User-Agent":"EuroSetu/1.0 (+https://eurosetu.trade)"},method="POST"); urllib.request.urlopen(req,timeout=6).read()
 except Exception as e:print(f"[notify] worker notify failed: {e}",flush=True)
def require_lead(request:Request):
 token=request.headers.get("x-eurosetu-lead-token") or request.query_params.get("lead_token")
 if not token:raise HTTPException(403,"Demo access requires the contact form (POST /api/leads) first")
 with connect() as conn:
  hit=row(conn,"SELECT id FROM leads WHERE token=?",(token,))
 if not hit:raise HTTPException(403,"Invalid demo access token")
 return token
@app.on_event("startup")
def startup():
 if os.getenv("EUROSETU_ENV")=="production":
  if not os.getenv("EUROSETU_DEPLOYMENT_TENANT"):
   raise RuntimeError("Production requires EUROSETU_DEPLOYMENT_TENANT")
  if not (os.getenv("EUROSETU_JWT_SECRET") or os.getenv("EUROSETU_OIDC_JWKS_URL")):
   raise RuntimeError("Production requires authentication configuration")
  if os.getenv("DATABASE_URL"):
   raise RuntimeError("DATABASE_URL is unsupported by this SQLite deployment; use EUROSETU_DB_PATH on a persistent volume")
 init_db()
 if os.getenv("EUROSETU_ENV")=="production":
  from .production_storage import validate_single_tenant_storage
  validate_single_tenant_storage(os.environ["EUROSETU_DEPLOYMENT_TENANT"])
  if os.getenv("EUROSETU_RECURRING_SAAS_ENABLED")=="1":
   from .commercial_gate import assess
   gate=assess(os.environ["EUROSETU_DEPLOYMENT_TENANT"])
   if not gate["ready_for_recurring_saas"]:raise RuntimeError("Recurring SaaS release gate closed: "+", ".join(gate["blockers"]))
 else:seed_if_empty()

@app.get("/health/ready")
def readiness():
 try:
  with connect() as conn:
   result=conn.execute("PRAGMA quick_check").fetchone()[0]
   if result!="ok":raise RuntimeError(result)
  if os.getenv("EUROSETU_ENV")=="production" and os.getenv("EUROSETU_RECURRING_SAAS_ENABLED")=="1":
   from .commercial_gate import assess
   if not assess(os.environ["EUROSETU_DEPLOYMENT_TENANT"],quick=True)["ready_for_recurring_saas"]:
    raise RuntimeError("Commercial release gate closed")
 except Exception:raise HTTPException(503,"Operational database is not ready")
 return {"status":"ready"}
def find_shipment(conn,ref):
 s=row(conn,"SELECT * FROM shipments WHERE id=? OR shipment_no=?",(ref,ref))
 if not s:raise HTTPException(404,"shipment not found")
 return s
def detailed(conn,s):
 req=rows(conn,"SELECT * FROM requirements WHERE shipment_id=? ORDER BY blocking DESC,category,code",(s["id"],)); ver=row(conn,"SELECT * FROM verifications WHERE shipment_id=? ORDER BY started_at DESC LIMIT 1",(s["id"],)); cycle=None
 if ver and ver.get("completed_at"):cycle=(datetime.fromisoformat(ver["completed_at"])-datetime.fromisoformat(ver["started_at"])).total_seconds()/86400
 return {**s,"requirements":req,"public_sources":rows(conn,"SELECT * FROM public_sources WHERE shipment_id=? ORDER BY id",(s["id"],)),"verification":ver,"verification_cycle_days":round(cycle,1) if cycle is not None else None,"score":shipment_score(s,req,ver)}
@app.get("/",response_class=HTMLResponse)
def home():
 if os.getenv("EUROSETU_ENV")=="production" and os.getenv("EUROSETU_SPLIT_HOSTS")=="1":return RedirectResponse("/pilot",status_code=302)
 p=STATIC/"index.html"
 return FileResponse(p) if p.exists() else HTMLResponse("<h1>EuroSetu</h1>")
@app.get("/trust",response_class=HTMLResponse)
def trust():return FileResponse(STATIC/"trust.html")
@app.get("/case-study",response_class=HTMLResponse)
def case_study():return FileResponse(STATIC/"case-study.html")
@app.get("/case-study-run",response_class=HTMLResponse)
def case_study_run():
 if os.getenv("EUROSETU_ENV")=="production":return RedirectResponse("/real-dossier",status_code=302)
 return FileResponse(STATIC/"case-study-run.html")
@app.get("/benchmarks",response_class=HTMLResponse)
def benchmarks_page():return FileResponse(STATIC/"benchmarks.html",headers={"Cache-Control":"no-cache, no-store, must-revalidate"})
@app.get("/benchmarks.js")
def benchmarks_js():return FileResponse(STATIC/"benchmarks.js",media_type="application/javascript",headers={"Cache-Control":"no-cache, no-store, must-revalidate"})
@app.get("/case-study.js")
def case_study_js():return FileResponse(STATIC/"case-study.js",media_type="application/javascript")
WEB_BENCH=Path(__file__).resolve().parents[1]/"web"/"benchmarks"
def _read_release_json(commit:str,name:str):
 p=(WEB_BENCH/commit/name).resolve()
 if WEB_BENCH.resolve() not in p.parents:raise HTTPException(400,"invalid release ref")
 if not p.exists():raise HTTPException(404,"release artifact not found")
 return json.loads(p.read_text())
@app.get("/api/benchmarks/releases")
def benchmark_releases():
 idx=WEB_BENCH/"releases.json"
 if not idx.exists():return []
 return json.loads(idx.read_text())
@app.get("/api/benchmarks/releases/{commit}")
def benchmark_release_summary(commit:str):
 return _read_release_json(commit,"summary.json")
@app.get("/api/benchmarks/releases/{commit}/results")
def benchmark_release_results(commit:str):
 return _read_release_json(commit,"results.json")
@app.get("/api/benchmarks/releases/{commit}/cases/{suite_id}/{case_id}")
def benchmark_release_case(commit:str,suite_id:str,case_id:str):
 for r in _read_release_json(commit,"results.json"):
  if r.get("suite_id")==suite_id and r.get("case_id")==case_id:return r
 raise HTTPException(404,"case not in this release")
@app.get("/demo",response_class=HTMLResponse)
def demo():
 if os.getenv("EUROSETU_ENV")=="production" and os.getenv("EUROSETU_SPLIT_HOSTS")=="1":return RedirectResponse("/real-dossier",status_code=302)
 p=STATIC/"demo.html"
 return FileResponse(p) if p.exists() else FileResponse(STATIC/"dashboard.html")
@app.get("/demo.js")
def demo_js():return FileResponse(STATIC/"demo.js",media_type="application/javascript")
@app.get("/demo.css")
def demo_css():return FileResponse(STATIC/"demo.css",media_type="text/css")
@app.post("/api/leads",status_code=201)
def leads_create(x:LeadIn):
 email=x.work_email.strip().lower()
 if not EMAIL_RE.match(email):raise HTTPException(422,"Valid work email required")
 if not x.name.strip() or not x.company.strip():raise HTTPException(422,"Name and company required")
 now=datetime.now(timezone.utc).isoformat()
 with connect() as conn:
  existing=row(conn,"SELECT id,token FROM leads WHERE work_email=?",(email,))
  if existing:return {"lead_id":existing["id"],"token":existing["token"],"returning":True}
  lid=str(uuid4()); token=secrets.token_urlsafe(24)
  conn.execute("INSERT INTO leads(id,name,work_email,company,role,message,token,created_at) VALUES(?,?,?,?,?,?,?,?)",(lid,x.name.strip(),email,x.company.strip(),(x.role or "").strip() or None,(x.message or "").strip() or None,token,now))
  audit(conn,None,"lead.created",{"lead_id":lid,"company":x.company.strip()})
  _notify_founder({"kind":"demo lead","email":email,"name":x.name.strip(),"company":x.company.strip(),"role":(x.role or "").strip(),"message":(x.message or "").strip()})
  return {"lead_id":lid,"token":token,"returning":False}
@app.get("/api/leads/verify")
def leads_verify(request:Request):
 try:token=require_lead(request)
 except HTTPException:return {"valid":False}
 with connect() as conn:
  hit=row(conn,"SELECT name,company FROM leads WHERE token=?",(token,))
 return {"valid":True,"name":hit["name"],"company":hit["company"]} if hit else {"valid":False}
@app.post("/api/contact",status_code=201)
def contact_create(x:ContactIn):
 # Honeypot: a filled "website" field means a bot. Accept silently so the bot
 # does not learn the trap, but never persist the submission.
 if (x.website or "").strip():return {"received":True,"id":None}
 email=x.work_email.strip().lower()
 if not EMAIL_RE.match(email):raise HTTPException(422,"Valid work email required")
 if not x.name.strip():raise HTTPException(422,"Name required")
 topic=(x.topic or "General enquiry").strip()[:120] or "General enquiry"
 cid=str(uuid4()); now=datetime.now(timezone.utc).isoformat()
 with connect() as conn:
  conn.execute("INSERT INTO contacts(id,name,work_email,company,topic,message,created_at) VALUES(?,?,?,?,?,?,?)",(cid,x.name.strip(),email,(x.company or "").strip() or None,topic,(x.message or "").strip() or None,now))
  audit(conn,None,"contact.created",{"contact_id":cid,"topic":topic})
  _notify_founder({"kind":"contact","email":email,"name":x.name.strip(),"company":(x.company or "").strip(),"topic":topic,"message":(x.message or "").strip()})
 return {"received":True,"id":cid,"topic":topic}
class AdminMintIn(BaseModel):
 email:str; tenant:str|None=None; roles:list[str]|None=None; days:int|None=None
@app.get("/admin",response_class=HTMLResponse)
def admin_page():
 p=STATIC/"admin.html"
 return FileResponse(p) if p.exists() else HTMLResponse("<h1>Admin queue not deployed</h1>",status_code=503)
@app.get("/api/admin/requests")
def admin_requests(request:Request):
 # Founder-only manual queue: every contact enquiry + demo lead, newest first,
 # so pilot@eurosetu.trade mail can be matched to a one-click key mint.
 # Also returns the pilot data-mode so /admin shows whether the live DB is
 # still the JSW demo showcase or already holds client rows.
 from .security import require_request
 require_request(request,"admin")
 with connect() as conn:
  contacts=rows(conn,"SELECT id,name,work_email,company,topic,message,created_at FROM contacts ORDER BY created_at DESC LIMIT 200")
  leads=rows(conn,"SELECT id,name,work_email,company,role,message,created_at FROM leads ORDER BY created_at DESC LIMIT 200")
 try:
  from .pilot import pilot_overview as _ov
  _o=_ov()
  _mode={"data_mode":_o.get("data_mode"),"demo_shipment_count":_o.get("demo_shipment_count",0),"client_shipment_count":_o.get("client_shipment_count",0)}
 except Exception:
  _mode={"data_mode":"UNKNOWN","demo_shipment_count":0,"client_shipment_count":0}
 return {"contacts":contacts,"leads":leads,**_mode}
@app.post("/api/admin/mint",status_code=201)
def admin_mint(x:AdminMintIn,request:Request):
 # Manual issuance: founder copies the returned bearer key into Gmail and
 # sends it to the requester. Nothing is auto-emailed from this endpoint.
 from .security import require_request
 p=require_request(request,"admin")
 from .pilot_keys import DEFAULT_DAYS,DEFAULT_ROLES,DEFAULT_TENANT,mint_pilot_key
 email=(x.email or "").strip().lower()
 if not EMAIL_RE.match(email):raise HTTPException(422,"Valid requester email required")
 tenant=(x.tenant or DEFAULT_TENANT or p.tenant_id).strip()
 roles=list(x.roles) if x.roles else list(DEFAULT_ROLES)
 days=int(x.days) if x.days else DEFAULT_DAYS
 secret=os.getenv("EUROSETU_JWT_SECRET")
 if not secret:raise HTTPException(503,"Production authentication is not configured")
 try:token=mint_pilot_key(secret,tenant,roles,days,email)
 except ValueError as e:raise HTTPException(422,str(e))
 with connect() as conn:
  audit(conn,None,"pilot.key_minted",{"email":email,"tenant":tenant,"roles":roles,"days":days,"issued_by":p.subject})
 return {"email":email,"tenant":tenant,"roles":roles,"days":days,"token":token}
@app.get("/pilot",response_class=HTMLResponse)
def pilot():
 if os.getenv("EUROSETU_ENV")=="production" and os.getenv("EUROSETU_SPLIT_HOSTS")=="1":return RedirectResponse("/real-dossier",status_code=302)
 # Public shell: the HTML loads for everyone so we can show a friendly
 # "Pilot access required - contact us" popup. The data APIs below stay
 # bearer-gated, so no pilot data leaks without a token.
 return FileResponse(STATIC/"pilot.html")
@app.get("/pilot.js")
def pilot_js():return FileResponse(STATIC/"pilot.js",media_type="application/javascript")
@app.get("/api/pilot/overview")
def pilot_overview(request:Request):
 from .security import require_request
 require_request(request,"pilot_viewer","pilot_contributor","verifier","admin")
 from .pilot import pilot_overview as _overview
 return _overview()
@app.post("/api/pilot/shipments/{shipment_id}/simulate-remediation")
def pilot_simulate_remediation(shipment_id,x:RemediationSimulationIn,request:Request):
 from .security import require_request
 require_request(request,"pilot_viewer","pilot_contributor","verifier","admin")
 from .risk_drilldown import simulate_remediation
 try:return simulate_remediation(shipment_id,x.requirement_code,x.estimated_cost_eur)
 except ValueError as e:raise HTTPException(422,str(e))
@app.post("/api/pilot/remediation/requests",status_code=201)
def pilot_remediation_create(x:EvidenceRequestIn,request:Request):
 from .security import require_request
 require_request(request,"pilot_contributor","admin")
 from .evidence_network import create_request
 try:return create_request(**x.model_dump())
 except ValueError as e:raise HTTPException(422,str(e))
@app.post("/api/pilot/suppliers/{supplier_id}/evidence",status_code=201)
def pilot_evidence_submit(supplier_id,x:SupplierEvidenceSubmitIn,request:Request):
 from .security import require_request
 require_request(request,"pilot_contributor","admin")
 from .evidence_network import add_supplier_evidence
 try:return add_supplier_evidence(supplier_id,evidence_type=x.evidence_type,content=x.content,issuer=x.issuer,source_ref=x.source_ref)
 except ValueError as e:raise HTTPException(422,str(e))
@app.post("/api/pilot/evidence/{evidence_id}/verify")
def pilot_evidence_verify(evidence_id,x:SupplierEvidenceVerifyIn,request:Request):
 from .security import require_request
 p=require_request(request,"verifier","admin")
 x.verifier=p.subject
 from .evidence_network import verify_supplier_evidence
 try:return verify_supplier_evidence(evidence_id,x.verifier)
 except ValueError as e:raise HTTPException(422,str(e))
@app.post("/api/pilot/remediation/requests/{request_id}/resolve")
def pilot_remediation_resolve(request_id,x:EvidenceResolveIn,request:Request):
 from .security import require_request
 require_request(request,"verifier","admin")
 from .evidence_network import resolve_request
 try:return resolve_request(request_id,x.evidence_id)
 except ValueError as e:raise HTTPException(422,str(e))
@app.get("/favicon.svg")
def favicon_svg():return FileResponse(STATIC/"favicon.svg",media_type="image/svg+xml")
@app.get("/robots.txt")
def robots():return Response("User-agent: *\nAllow: /\nSitemap: /sitemap.xml\n",media_type="text/plain")
@app.get("/sitemap.xml")
def sitemap():return Response('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>/</loc></url><url><loc>/demo</loc></url><url><loc>/pilot</loc></url><url><loc>/case-study</loc></url><url><loc>/benchmarks</loc></url><url><loc>/trust</loc></url><url><loc>/product</loc></url><url><loc>/workflow</loc></url><url><loc>/pricing</loc></url><url><loc>/brokers</loc></url><url><loc>/workflow-run</loc></url><url><loc>/liability-preview</loc></url><url><loc>/threshold-checker</loc></url><url><loc>/carbon-price-relief</loc></url><url><loc>/cbam-rate</loc></url><url><loc>/guides</loc></url><url><loc>/faq</loc></url><url><loc>/sectors</loc></url><url><loc>/account</loc></url><url><loc>/changelog</loc></url><url><loc>/worked-example</loc></url><url><loc>/supplier-data-template</loc></url><url><loc>/security</loc></url><url><loc>/privacy</loc></url><url><loc>/terms</loc></url><url><loc>/dpa</loc></url></urlset>',media_type="application/xml")
@app.get("/product",response_class=HTMLResponse)
def product():
 from .content_hub import shell as _shell
 from .content_pages import product_page
 t,d,b=product_page(); return HTMLResponse(_shell(t,d,b))
@app.get("/workflow",response_class=HTMLResponse)
def workflow():
 from .content_hub import shell as _shell
 from .content_pages import workflow_page
 t,d,b=workflow_page(); return HTMLResponse(_shell(t,d,b))
@app.get("/pricing",response_class=HTMLResponse)
def pricing():
 from .content_hub import shell as _shell
 from .content_pages import pricing_page
 t,d,b=pricing_page(); return HTMLResponse(_shell(t,d,b))
@app.get("/brokers",response_class=HTMLResponse)
def brokers():
 from .content_hub import shell as _shell
 from .content_pages import brokers_page
 t,d,b=brokers_page(); return HTMLResponse(_shell(t,d,b))
@app.get("/liability-preview",response_class=HTMLResponse)
def liability_preview():
 from .content_hub import shell as _shell
 from .content_pages import liability_page
 t,d,b,x=liability_page(); return HTMLResponse(_shell(t,d,b,x))
@app.get("/threshold-checker",response_class=HTMLResponse)
def threshold_checker():
 from .content_hub import shell as _shell
 from .content_pages import threshold_page
 t,d,b,x=threshold_page(); return HTMLResponse(_shell(t,d,b,x))
@app.get("/carbon-price-relief",response_class=HTMLResponse)
def carbon_relief():
 from .content_hub import shell as _shell
 from .content_pages import relief_page
 t,d,b,x=relief_page(); return HTMLResponse(_shell(t,d,b,x))
@app.get("/cbam-rate",response_class=HTMLResponse)
def cbam_rate():
 from .content_hub import shell as _shell
 from .content_pages import rate_page
 t,d,b=rate_page(); return HTMLResponse(_shell(t,d,b))
@app.get("/guides",response_class=HTMLResponse)
def guides_index():
 from .content_hub import shell as _shell
 from .content_pages import guides_index_page
 t,d,b=guides_index_page(); return HTMLResponse(_shell(t,d,b))
@app.get("/guides/{slug}",response_class=HTMLResponse)
def guide_detail(slug:str):
 from .content_hub import shell as _shell
 from .content_pages import guide_page
 r=guide_page(slug)
 if not r:raise HTTPException(404,"guide not found")
 t,d,b=r; return HTMLResponse(_shell(t,d,b))
@app.get("/worked-example",response_class=HTMLResponse)
def worked_example():
 from .content_hub import shell as _shell
 from .content_pages import worked_example_page
 t,d,b=worked_example_page(); return HTMLResponse(_shell(t,d,b))
@app.get("/supplier-data-template",response_class=HTMLResponse)
def supplier_template():
 from .content_hub import shell as _shell
 from .content_pages import supplier_template_page
 t,d,b=supplier_template_page(); return HTMLResponse(_shell(t,d,b))
@app.get("/security",response_class=HTMLResponse)
def security_page():
 from .content_hub import shell as _shell
 from .content_pages import security_page as _sp
 t,d,b=_sp(); return HTMLResponse(_shell(t,d,b))
@app.get("/privacy",response_class=HTMLResponse)
def privacy():
 from .content_hub import shell as _shell
 from .content_pages import legal_page
 t,d,b=legal_page("privacy"); return HTMLResponse(_shell(t,d,b))
@app.get("/dpa",response_class=HTMLResponse)
def dpa():
 from .content_hub import shell as _shell
 from .content_pages import legal_page
 t,d,b=legal_page("dpa"); return HTMLResponse(_shell(t,d,b))
@app.get("/terms",response_class=HTMLResponse)
def terms():
 from .content_hub import shell as _shell
 from .content_pages import legal_page
 t,d,b=legal_page("terms"); return HTMLResponse(_shell(t,d,b))
@app.get("/faq",response_class=HTMLResponse)
def faq():
 from .content_hub import shell as _shell
 from .content_pages import faq_page
 t,d,b=faq_page(); return HTMLResponse(_shell(t,d,b))
@app.get("/sectors",response_class=HTMLResponse)
def sectors():
 from .content_hub import shell as _shell
 from .content_pages import sectors_page
 t,d,b=sectors_page(); return HTMLResponse(_shell(t,d,b))
@app.get("/account",response_class=HTMLResponse)
def account():
 from .content_hub import shell as _shell
 from .content_pages import account_page
 t,d,b=account_page(); return HTMLResponse(_shell(t,d,b))
@app.get("/changelog",response_class=HTMLResponse)
def changelog():
 from .content_hub import shell as _shell
 from .content_pages import changelog_page
 t,d,b=changelog_page(); return HTMLResponse(_shell(t,d,b))
class ToolLedgerIn(BaseModel):lines:list=[]; year:int=2026; certificate_price_eur:float|None=None; default_origin:str="IN"
class ToolThresholdIn(BaseModel):mass_t:float=0; uk_value_gbp:float|None=None
class ToolReliefIn(BaseModel):embedded_tco2e:float=0; certificate_price_eur:float=85; reduction_certificates:float=0; faa_tco2e:float=0
@app.post("/api/tools/liability-preview")
def tool_liability(x:ToolLedgerIn):
 from .content_pages import api_liability_preview
 return api_liability_preview(x.model_dump())
@app.post("/api/tools/threshold")
def tool_threshold(x:ToolThresholdIn):
 from .content_pages import api_threshold
 return api_threshold(x.model_dump())
@app.post("/api/tools/relief-estimate")
def tool_relief(x:ToolReliefIn):
 from .content_pages import api_relief_estimate
 return api_relief_estimate(x.model_dump())
@app.get("/api/tools/supplier-template.csv")
def tool_supplier_csv():
 from .content_pages import SUPPLIER_CSV
 return Response(SUPPLIER_CSV,media_type="text/csv",headers={"Content-Disposition":"attachment; filename=eurosetu-supplier-template.csv"})
@app.get("/workflow-run",response_class=HTMLResponse)
def workflow_run():
 from .content_hub import shell as _shell
 from .content_pages import workflow_run_page
 t,d,b,x=workflow_run_page(); return HTMLResponse(_shell(t,d,b,x))
@app.get("/api/workflow-run/model-config")
def workflow_run_model_config():
 from .llm_document_ingest import settings
 config=settings()
 return {"default_model":config["default_model"],
         "base_url":config["base_url"], "key_configured":config["api_key_configured"],
         "auth_required":True, "pdf_only":True}

@app.post("/api/workflow-run/parse")
async def workflow_run_parse(request:Request):
 from fastapi.concurrency import run_in_threadpool
 from .content_pages import api_workflow_run_parse
 form=await request.form()
 use_llm=str(form.get("use_llm") or "").lower() in ("1","true","on","yes")
 if use_llm:
  from .security import require_request
  require_request(request,"pilot_contributor","admin")
 files: list[tuple[str, bytes]] = []
 for v in form.getlist("files"):
  fn = getattr(v, "filename", None)
  if fn is not None:
   files.append((fn or "upload", await v.read()))
 pasted=str(form.get("pasted_csv") or ""); doc_url=str(form.get("doc_url") or "")
 if use_llm and sum(name.lower().endswith(".pdf") for name,_ in files)>3:
  raise HTTPException(413,"At most three PDFs per model-assisted request")
 compare_ocr=str(form.get("compare_ocr") or "").lower() in ("1","true","on","yes")
 result=await run_in_threadpool(api_workflow_run_parse,files,pasted,doc_url,compare_ocr)
 if use_llm:
  from .llm_document_ingest import propose_pdf_lines
  model=str(form.get("model_id") or "").strip() or None
  for (name,data),doc in zip(files,result["documents"]):
   if not name.lower().endswith(".pdf") or not doc.get("ok"):
    continue
   proposal=await propose_pdf_lines(data,name,model)
   doc["llm_proposal"]=proposal
   if proposal.get("lines"):
    doc["candidates"]=proposal["lines"]
    doc["structured_ingestion"]=proposal
 return result
class WorkflowRunCompileIn(BaseModel):lines:list=[]; source_conflicts:list=[]; importer_cbam_mass_ytd_t:float=0; seed_demo_taric:bool=True; demo_cbam_pack:bool=False; authorised_cbam_declarant:bool=True; cbam_emissions_verified:bool=True
@app.post("/api/workflow-run/compile")
def workflow_run_compile(x:WorkflowRunCompileIn):
 from .content_pages import api_workflow_run_compile
 return api_workflow_run_compile(x.model_dump())
@app.get("/dossier-demo",response_class=HTMLResponse)
def dossier_demo_page():
 return FileResponse(STATIC/"dossier-demo.html")
@app.post("/api/dossiers/demo",status_code=201)
def dossier_demo_create(request:Request):
 from .security import require_request
 from .pilot_dossier import create_demo,get_dossier
 p=require_request(request,"pilot_contributor","admin")
 dossier_id=create_demo(p.tenant_id,p.subject)
 return get_dossier(dossier_id,p.tenant_id)
@app.get("/api/dossiers/{dossier_id}")
def dossier_get(dossier_id:str,request:Request):
 from .security import require_request
 from .pilot_dossier import get_dossier
 p=require_request(request,"pilot_viewer","pilot_contributor","verifier","admin")
 try:return get_dossier(dossier_id,p.tenant_id)
 except KeyError:raise HTTPException(404,"Dossier not found")
class DossierReviewIn(BaseModel):
 approve:bool
 reason:str
@app.post("/api/dossiers/{dossier_id}/documents/{document_id}/review")
def dossier_review(dossier_id:str,document_id:str,x:DossierReviewIn,request:Request):
 from .security import require_request
 from .pilot_dossier import review_document
 p=require_request(request,"verifier","admin")
 try:return review_document(dossier_id,p.tenant_id,document_id,p.subject,x.approve,x.reason)
 except KeyError:raise HTTPException(404,"Dossier or document not found")
 except ValueError as exc:raise HTTPException(409,str(exc))
@app.post("/api/dossiers/{dossier_id}/remediate/{role}")
def dossier_remediate(dossier_id:str,role:str,request:Request):
 from .security import require_request
 from .pilot_dossier import remediate
 p=require_request(request,"pilot_contributor","admin")
 try:return remediate(dossier_id,p.tenant_id,role,p.subject)
 except KeyError:raise HTTPException(404,"Dossier not found")
 except ValueError as exc:raise HTTPException(400,str(exc))
@app.get("/api/dossiers/{dossier_id}/documents/{document_id}/pdf")
def dossier_pdf(dossier_id:str,document_id:str,request:Request):
 from .security import require_request
 from .pilot_dossier import document_pdf
 p=require_request(request,"pilot_viewer","pilot_contributor","verifier","admin")
 try:data,name=document_pdf(dossier_id,p.tenant_id,document_id)
 except KeyError:raise HTTPException(404,"Dossier or document not found")
 except ValueError as exc:raise HTTPException(409,str(exc))
 return Response(data,media_type="application/pdf",headers={"Content-Disposition":f'inline; filename="{name}"',"Cache-Control":"no-store"})
@app.get("/app.js")
def js():return FileResponse(STATIC/"app.js",media_type="application/javascript")
@app.get("/styles.css")
def css():return FileResponse(STATIC/"styles.css",media_type="text/css")
@app.get("/public.css")
def public_css():return FileResponse(STATIC/"public.css",media_type="text/css",headers={"Cache-Control":"no-cache, no-store, must-revalidate"})
@app.get("/public.js")
def public_js():return FileResponse(STATIC/"public.js",media_type="application/javascript")
@app.get("/api/dashboard")
def dashboard(request:Request):
 require_lead(request)
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
  s=find_shipment(conn,shipment_id); shipment_id=s["id"]
  req=row(conn,"SELECT * FROM requirements WHERE shipment_id=? AND code=?",(shipment_id,x.requirement_code))
  if not req:raise HTTPException(404,"requirement not found")
  conn.execute("INSERT INTO evidence(id,shipment_id,requirement_code,filename,evidence_type,issuer,sha256,valid_until,created_at) VALUES(?,?,?,?,?,?,?,?,?)",(eid,shipment_id,x.requirement_code,x.filename,x.evidence_type,x.issuer,sha,x.valid_until,datetime.now(timezone.utc).isoformat()))
  count=conn.execute("SELECT COUNT(*) FROM evidence WHERE shipment_id=? AND requirement_code=?",(shipment_id,x.requirement_code)).fetchone()[0]; conn.execute("UPDATE requirements SET evidence_count=? WHERE shipment_id=? AND code=?",(count,shipment_id,x.requirement_code))
  if count>=req["required_evidence"] and x.requirement_code not in ("CBAM_VERIFICATION","SUPPLIER_DATA","CBAM_EMISSIONS"):conn.execute("UPDATE requirements SET status='PASS' WHERE shipment_id=? AND code=?",(shipment_id,x.requirement_code))
  audit(conn,shipment_id,"evidence.added",{"id":eid,"requirement":x.requirement_code,"sha256":sha}); return {"id":eid,"sha256":sha,"evidence_count":count}
@app.get("/api/shipments/{shipment_id}/dpp")
def dpp(shipment_id):
 with connect() as conn:
  s=find_shipment(conn,shipment_id)
  if not s:raise HTTPException(404,"shipment not found")
  d=detailed(conn,s); return {"@context":["https://schema.org/"],"passport":{"id":f"urn:eurosetu:dpp:{s['id']}","status":"MVP_READINESS","schemaVersion":"steel-v0.1"},"product":{"uniqueProductIdentifier":s["shipment_no"],"name":s["product"],"commodityCode":s["cn_code"],"manufacturer":s["exporter"],"facility":s["facility"],"massTonnes":s["tonnes"]},"environment":{"embeddedEmissions":{"value":s["embedded_emissions_tco2e_per_t"],"unit":"tCO2e/t"}},"compliance":{"autoReady":d["score"]["auto_ready"],"readinessScore":d["score"]["readiness_score"],"blockers":d["score"]["blockers"]},"notice":"MVP readiness payload; final steel ESPR fields remain versioned/configurable."}
@app.get("/api/market-access/order-book")
def market_access_order_book(request:Request):
 require_lead(request)
 from .market_access import order_book
 return order_book()
@app.get("/api/market-access/risk-drilldown")
def market_access_risk_drilldown(request:Request):
 require_lead(request)
 from .risk_drilldown import risk_drilldown
 return risk_drilldown()
@app.post("/api/market-access/shipments/{shipment_id}/simulate-remediation")
def market_access_simulate_remediation(shipment_id,x:RemediationSimulationIn,request:Request):
 require_lead(request)
 from .risk_drilldown import simulate_remediation
 try:return simulate_remediation(shipment_id,x.requirement_code,x.estimated_cost_eur)
 except ValueError as e:raise HTTPException(422,str(e))
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
def remediation(request:Request):
 require_lead(request)
 from .evidence_network import remediation_summary
 return remediation_summary()
@app.post("/api/remediation/requests",status_code=201)
def remediation_create(x:EvidenceRequestIn,request:Request):
 require_lead(request)
 from .evidence_network import create_request
 try:return create_request(**x.model_dump())
 except ValueError as e:raise HTTPException(422,str(e))
@app.post("/api/remediation/requests/{request_id}/resolve")
def remediation_resolve(request_id,x:EvidenceResolveIn):
 from .evidence_network import resolve_request
 try:return resolve_request(request_id,x.evidence_id)
 except ValueError as e:raise HTTPException(422,str(e))
@app.get("/api/integrations")
def integrations_catalog(request:Request):
 require_lead(request)
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
@app.post("/api/cbam/verification/validate")
def cbam_verification_validate(x:CBAMVerificationReportIn):
 from .cbam_verification import verification_state
 return verification_state(x.payload)
@app.get("/api/cbam/calculations")
def cbam_calculations():
 from .cbam_engine import list_calculations
 return {"calculations":list_calculations()}
@app.post("/api/regulatory/steel/evaluate")
def regulatory_steel_evaluate(x:RegulatoryPayloadIn):
 from .steel_trade_engine_v2 import evaluate
 try:return evaluate(x.payload)
 except (ValueError,KeyError) as e:raise HTTPException(422,str(e))
@app.post("/api/regulatory/steel/categories/import")
def regulatory_steel_categories_import(x:ReferenceCSVIn):
 from .steel_trade_engine_v2 import import_categories
 try:return import_categories(x.csv_content)
 except (ValueError,KeyError) as e:raise HTTPException(422,str(e))
@app.post("/api/cbam/v2/calculate")
def cbam_v2_calculate(x:RegulatoryPayloadIn):
 from .cbam_definitive_v2 import calculate
 try:return calculate(x.payload)
 except (ValueError,KeyError) as e:raise HTTPException(422,str(e))
@app.post("/api/cbam/v2/defaults/import")
def cbam_defaults_import(x:ReferenceCSVIn):
 from .cbam_definitive_v2 import import_defaults
 return import_defaults(x.csv_content)
@app.post("/api/cbam/v2/benchmarks/import")
def cbam_benchmarks_import(x:ReferenceCSVIn):
 from .cbam_definitive_v2 import import_benchmarks
 return import_benchmarks(x.csv_content)
@app.post("/api/cbam/v2/cscf/import")
def cbam_cscf_import(x:RegulatoryPayloadIn):
 from .cbam_definitive_v2 import import_cscf
 return import_cscf(x.payload)
@app.post("/api/cbam/verification/pack")
def cbam_verification_pack(x:RegulatoryPayloadIn):
 from .cbam_verification_pack import build_pack
 return build_pack(x.payload)
@app.post("/api/market-access/v2/compile")
def market_access_v2_compile(x:RegulatoryPayloadIn):
 from .market_access_compiler_v2 import compile_shipment
 from .readiness import submission_readiness
 try:
  result=compile_shipment(x.payload)
  return {**result,**submission_readiness(result)}
 except (ValueError,KeyError) as e:raise HTTPException(422,str(e))
@app.post("/api/customs/declaration-readiness")
def customs_declaration_readiness(x:RegulatoryPayloadIn):
 from .customs_declaration_pack import compile_pack
 try:return compile_pack(x.payload)
 except ValueError as e:raise HTTPException(422,str(e))
@app.post("/api/customs/taric/resolve")
def customs_taric_resolve(x:TaricResolveIn):
 from .taric_engine import resolve_taric
 p=x.payload
 required=("cn_code","origin_country","import_date","customs_value_eur","quantity_t")
 missing=[k for k in required if k not in p]
 if missing:raise HTTPException(422,"Missing required fields")
 try:return resolve_taric(p["cn_code"],p["origin_country"],p["import_date"],p["customs_value_eur"],p["quantity_t"],p.get("customs_documents"),p.get("additional_code"))
 except ValueError as e:raise HTTPException(422,str(e))
@app.get("/api/regulatory/public-data/status")
def regulatory_public_data_status():
 from .eu_public_data import latest,freshness
 return {"taric":{"snapshot":latest("taric"),"freshness":freshness(latest("taric"))},"quota":{"snapshot":latest("quota"),"freshness":freshness(latest("quota"))}}
@app.post("/api/regulatory/public-data/{kind}/import")
def regulatory_public_data_import(kind,x:PublicDataImportIn):
 from .eu_public_data import parse_csv,store_snapshot
 if kind not in ("taric","quota"):raise HTTPException(404,"kind must be taric or quota")
 try:return store_snapshot(kind,parse_csv(x.csv_content,kind,x.as_of),x.csv_content.encode())
 except Exception as e:raise HTTPException(422,str(e))
@app.post("/api/regulatory/public-data/{kind}/sync")
def regulatory_public_data_sync(kind,x:PublicDataSyncIn):
 from .eu_public_data import sync_from_url
 if kind not in ("taric","quota"):raise HTTPException(404,"kind must be taric or quota")
 try:return sync_from_url(kind,x.url,x.as_of)
 except Exception as e:raise HTTPException(502,str(e))
@app.get("/api/regulatory/change-impact")
def regulatory_change_impact(request:Request,status:str|None=None):
 from .security import require_request
 require_request(request,"pilot_viewer","pilot_contributor","verifier","admin")
 from .regulatory_impact import queue
 return {"impacts":queue(status),"model":"source hash change -> affected shipment -> rule family -> review queue"}
@app.get("/api/regulatory/registry")
def regulatory_registry(as_of:str|None=None):
 from .regulatory_registry import registry
 try:return registry(as_of)
 except ValueError:raise HTTPException(422,"as_of must be YYYY-MM-DD")
@app.get("/api/regulatory/steel-measure")
def regulatory_steel_measure():
 from .steel_trade_measure import public_dataset
 return public_dataset()
@app.post("/api/compliance/active-entitlement")
def active_entitlement(x:ActiveEntitlementIn):
 from .compliance_entitlement import compile_active_entitlement
 try:return compile_active_entitlement(x.payload)
 except ValueError as e:raise HTTPException(422,str(e))
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


@app.get("/api/data-sources")
def data_source_status():
 from .data_sources import status
 return status()

@app.get("/api/data-sources/{dataset}")
def data_source_detail(dataset:str):
 from .data_sources import registry,status
 if dataset not in registry(): raise HTTPException(404,"Unknown dataset")
 return status()[dataset]

@app.post("/api/data-sources/{dataset}/snapshot")
def data_source_snapshot(dataset:str,provider_id:str|None=None):
 from .data_sources import registry,snapshot
 if dataset not in registry(): raise HTTPException(404,"Unknown dataset")
 try:return snapshot(dataset,provider_id)
 except ValueError as e:raise HTTPException(422,str(e))

class SourceSyncIn(BaseModel):as_of:str|None=None; url:str|None=None; force:bool=False
@app.post("/api/data-sources/{dataset}/sync")
def data_source_sync(dataset:str,x:SourceSyncIn):
 """Manual refresh: run the versioned resolver pipeline now.

 Body: {"as_of": "2026-09-29"} pins the version folder; {"url": ...}
 overrides the distribution URL; {"force": true} re-fetches even when
 today's manifest already exists. Browser-downloaded files (ECHA 403,
 FSF auth) are ingested via the sync_sources.py --file CLI path.
 """
 from .data_sources import registry
 if dataset not in registry(): raise HTTPException(404,"Unknown dataset")
 try:
  import sys; sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
  from scripts.sync_sources import sync_dataset
  return sync_dataset(dataset,as_of=x.as_of,url=x.url,force=x.force)
 except ValueError as e:raise HTTPException(422,str(e))
 except RuntimeError as e:raise HTTPException(422,str(e))

@app.get("/api/data-sources/{dataset}/manifest")
def data_source_manifest(dataset:str):
 from .data_sources import registry
 if dataset not in registry(): raise HTTPException(404,"Unknown dataset")
 from .source_resolvers import latest_manifest
 man=latest_manifest(dataset)
 if not man:raise HTTPException(404,"No manifest yet -- POST /api/data-sources/"+dataset+"/sync first")
 return man

class RealDossierCreateIn(BaseModel):
 name:str=Field(min_length=1,max_length=160)

@app.get("/real-dossier",response_class=HTMLResponse)
def real_dossier_page():
 return FileResponse(STATIC/"real-dossier.html")

@app.post("/api/real-dossiers",status_code=201)
def real_dossier_create(x:RealDossierCreateIn,request:Request):
 from .security import require_request
 from .real_evidence import create,get
 p=require_request(request,"pilot_contributor","admin")
 return get(create(p.tenant_id,p.subject,x.name),p.tenant_id)

@app.post("/api/real-dossiers/{dossier_id}/documents",status_code=201)
async def real_dossier_upload(dossier_id:str,request:Request):
 from fastapi.concurrency import run_in_threadpool
 from .security import require_request
 from .real_evidence import add_document,get
 p=require_request(request,"pilot_contributor","admin")
 form=await request.form()
 file=form.get("file")
 if not file or not getattr(file,"filename",None):raise HTTPException(400,"File required")
 data=await file.read(8*1024*1024+1)
 try:
  await run_in_threadpool(add_document,dossier_id,p.tenant_id,p.subject,file.filename,data)
  return await run_in_threadpool(get,dossier_id,p.tenant_id)
 except KeyError:raise HTTPException(404,"Dossier not found")
 except ValueError as exc:raise HTTPException(400,str(exc))

@app.get("/api/real-dossiers/{dossier_id}")
def real_dossier_get(dossier_id:str,request:Request):
 from .security import require_request
 from .real_evidence import get
 p=require_request(request,"pilot_viewer","pilot_contributor","verifier","admin")
 try:return get(dossier_id,p.tenant_id)
 except KeyError:raise HTTPException(404,"Dossier not found")

@app.post("/api/real-dossiers/{dossier_id}/documents/{document_id}/review")
def real_dossier_review(dossier_id:str,document_id:str,x:DossierReviewIn,request:Request):
 from .security import require_request
 from .real_evidence import review_document,get
 p=require_request(request,"verifier","admin")
 try:
  review_document(dossier_id,p.tenant_id,document_id,p.subject,x.approve,x.reason)
  return get(dossier_id,p.tenant_id)
 except KeyError:raise HTTPException(404,"Dossier or document not found")
 except ValueError as exc:raise HTTPException(409,str(exc))

@app.get("/api/real-dossiers/{dossier_id}/documents/{document_id}/file")
def real_dossier_file(dossier_id:str,document_id:str,request:Request):
 from .security import require_request
 from .real_evidence import document_bytes
 p=require_request(request,"pilot_viewer","pilot_contributor","verifier","admin")
 try:data,name=document_bytes(dossier_id,p.tenant_id,document_id)
 except KeyError:raise HTTPException(404,"Dossier or document not found")
 except ValueError as exc:raise HTTPException(409,str(exc))
 media="application/pdf" if name.lower().endswith(".pdf") else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
 return Response(data,media_type=media,headers={"Content-Disposition":f'attachment; filename="{name}"',"Cache-Control":"no-store"})

@app.post("/api/real-dossiers/{dossier_id}/links/{edge_id}/review")
def real_dossier_link_review(dossier_id:str,edge_id:str,x:DossierReviewIn,request:Request):
 from .security import require_request
 from .real_evidence import review_link,get
 p=require_request(request,"verifier","admin")
 try:
  review_link(dossier_id,p.tenant_id,edge_id,p.subject,x.approve,x.reason)
  return get(dossier_id,p.tenant_id)
 except KeyError:raise HTTPException(404,"Dossier or link not found")
 except ValueError as exc:raise HTTPException(409,str(exc))

class RealReleasePacketIn(BaseModel):
 packet:dict

@app.post('/api/real-dossiers/{dossier_id}/release-packets',status_code=201)
def real_release_submit(dossier_id:str,x:RealReleasePacketIn,request:Request):
 from .security import require_request
 from .real_release import submit
 from .real_evidence import get
 p=require_request(request,'pilot_contributor','admin')
 try:
  packet_id=submit(dossier_id,p.tenant_id,p.subject,x.packet)
  return {'packet_id':packet_id,'state':get(dossier_id,p.tenant_id)}
 except KeyError:raise HTTPException(404,'Dossier not found')
 except ValueError as exc:raise HTTPException(409,str(exc))

@app.post('/api/real-dossiers/{dossier_id}/release-packets/{packet_id}/review')
def real_release_review(dossier_id:str,packet_id:str,x:DossierReviewIn,request:Request):
 from .security import require_request
 from .real_release import decide
 from .real_evidence import get
 p=require_request(request,'verifier','admin')
 try:
  decide(dossier_id,p.tenant_id,packet_id,p.subject,x.approve,x.reason)
  return get(dossier_id,p.tenant_id)
 except KeyError:raise HTTPException(404,'Dossier or packet not found')
 except ValueError as exc:raise HTTPException(409,str(exc))

@app.get('/api/commercial/readiness')
def commercial_readiness(request:Request):
 from .security import require_request
 from .commercial_gate import assess
 p=require_request(request,'admin')
 return assess(p.tenant_id)


class RevokePrincipalIn(BaseModel):
 subject:str
 reason:str

@app.post('/api/admin/revoke-principal')
def revoke_principal(x:RevokePrincipalIn,request:Request):
 from .security import require_request
 import time
 p=require_request(request,'admin')
 subject=x.subject.strip()
 reason=x.reason.strip()
 if not subject or len(subject)>320 or not reason or len(reason)>1000:
  raise HTTPException(422,'Subject and substantive reason required')
 cutoff=int(time.time())
 with connect() as conn:
  conn.execute('INSERT INTO principal_revocations(tenant_id,subject,revoked_before,actor,reason,updated_at) VALUES(?,?,?,?,?,?) ON CONFLICT(tenant_id,subject) DO UPDATE SET revoked_before=MAX(principal_revocations.revoked_before,excluded.revoked_before),actor=excluded.actor,reason=excluded.reason,updated_at=excluded.updated_at',
               (p.tenant_id,subject,cutoff,p.subject,reason,datetime.now(timezone.utc).isoformat()))
 return {'tenant_id':p.tenant_id,'subject':subject,'revoked_before':cutoff}


@app.post('/api/real-dossiers/{dossier_id}/source-signoffs',status_code=201)
async def customer_source_submit(dossier_id:str,request:Request):
 from .security import require_request
 from .customer_source import submit
 p=require_request(request,'customer_signatory')
 form=await request.form()
 consent=form.get('consent_pdf')
 if not consent or not getattr(consent,'filename',None):
  raise HTTPException(400,'Signed consent PDF required')
 data=await consent.read(8*1024*1024+1)
 try:
  signoff_id=submit(dossier_id,p.tenant_id,p.subject,str(form.get('customer_name') or ''),
                    str(form.get('shipment_reference') or ''),str(form.get('reason') or ''),data)
  return {'signoff_id':signoff_id}
 except KeyError:raise HTTPException(404,'Dossier not found')
 except ValueError as exc:raise HTTPException(409,str(exc))

@app.post('/api/real-dossiers/{dossier_id}/source-signoffs/{signoff_id}/review')
def customer_source_review(dossier_id:str,signoff_id:str,x:DossierReviewIn,request:Request):
 from .security import require_request
 from .customer_source import decide
 p=require_request(request,'admin')
 try:
  decide(dossier_id,p.tenant_id,signoff_id,p.subject,x.approve,x.reason)
  return {'status':'APPROVED' if x.approve else 'REJECTED'}
 except KeyError:raise HTTPException(404,'Dossier or signoff not found')
 except ValueError as exc:raise HTTPException(409,str(exc))

@app.get('/api/real-dossiers/{dossier_id}/source-signoffs/{signoff_id}/consent')
def customer_source_consent(dossier_id:str,signoff_id:str,request:Request):
 from .security import require_request
 from .customer_source import consent_bytes
 p=require_request(request,'admin')
 try:
  data=consent_bytes(dossier_id,p.tenant_id,signoff_id)
  return Response(content=data,media_type='application/pdf',headers={'Cache-Control':'no-store','Content-Disposition':'attachment; filename="customer-consent.pdf"'})
 except KeyError:raise HTTPException(404,'Dossier or signoff not found')
 except ValueError as exc:raise HTTPException(409,str(exc))
