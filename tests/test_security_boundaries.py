import base64,hashlib,hmac,json,time
from fastapi.testclient import TestClient
from app.main import app
from app.db import init_db

def token(secret="test-secret",tenant="tenant-a",roles=("pilot_viewer",),sub="u1"):
 enc=lambda o:base64.urlsafe_b64encode(json.dumps(o,separators=(",",":")).encode()).rstrip(b"=").decode()
 h=enc({"alg":"HS256","typ":"JWT"});p=enc({"sub":sub,"exp":int(time.time())+3600,"tenant_id":tenant,"tenants":{tenant:list(roles)}})
 sig=base64.urlsafe_b64encode(hmac.new(secret.encode(),f"{h}.{p}".encode(),hashlib.sha256).digest()).rstrip(b"=").decode()
 return f"{h}.{p}.{sig}"

def headers(monkeypatch,roles=("pilot_viewer",),tenant="tenant-a"):
 monkeypatch.setenv("EUROSETU_JWT_SECRET","test-secret")
 return {"Authorization":"Bearer "+token(roles=roles,tenant=tenant),"x-eurosetu-tenant":tenant}

def test_demo_token_cannot_cross_into_pilot(monkeypatch):
 init_db();c=TestClient(app)
 lead=c.post("/api/leads",json={"name":"Demo User","work_email":"demo@example.com","company":"Example"}).json()["token"]
 assert c.get("/api/dashboard",headers={"x-eurosetu-lead-token":lead}).status_code==200
 assert c.get("/api/pilot/overview",headers={"x-eurosetu-lead-token":lead}).status_code==401

def test_signed_membership_cannot_assert_other_tenant(monkeypatch):
 monkeypatch.setenv("EUROSETU_JWT_SECRET","test-secret");c=TestClient(app)
 h={"Authorization":"Bearer "+token(tenant="tenant-a"),"x-eurosetu-tenant":"tenant-b"}
 assert c.get("/api/pilot/overview",headers=h).status_code==403

def test_viewer_cannot_mutate_or_verify(monkeypatch):
 c=TestClient(app);h=headers(monkeypatch,("pilot_viewer",))
 assert c.post("/api/pilot/remediation/requests",headers=h,json={"shipment_id":"x","supplier_id":"x","evidence_type":"x","owner":"x"}).status_code==403
 assert c.post("/api/pilot/evidence/x/verify",headers=h,json={"verifier":"spoofed"}).status_code==403

def test_tampered_token_rejected(monkeypatch):
 c=TestClient(app);h=headers(monkeypatch)
 h["Authorization"]=h["Authorization"][:-1]+("A" if h["Authorization"][-1]!="A" else "B")
 assert c.get("/api/pilot/overview",headers=h).status_code==401
