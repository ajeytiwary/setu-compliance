import hashlib
from fastapi import HTTPException
from app.security import Principal,require
from app.evidence_store import put,verify
from app.reference_validation import validate
from app.readiness import submission_readiness
def test_tenant_principal_and_roles():
 p=Principal("user-1","tenant-a",frozenset({"compliance_admin","viewer"}));assert p.tenant_id=="tenant-a";assert require(p,"compliance_admin")==p
 try: require(p,"owner"); assert False
 except HTTPException as e: assert e.status_code==403
def test_evidence_content_addressed(tmp_path,monkeypatch):
 import app.evidence_store as es
 monkeypatch.setattr(es,"ROOT",tmp_path)
 r=put("t1","s1","invoice.pdf",b"abc",{"issuer":"supplier"});assert r["sha256"]==hashlib.sha256(b"abc").hexdigest();assert verify("t1","s1",r["sha256"])
def test_reference_validation_fails_closed():
 assert not validate("x",b"x",[],1)["valid"];assert validate("x",b"x",[{"a":1}],1)["valid"]
def test_submission_semantics():
 r=submission_readiness({"blockers":[]});assert r["decision"]=="READY_FOR_SUBMISSION";assert r["authority_acceptance"]=="PENDING"
