import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import db
from app.main import app
from app.pilot_keys import mint_pilot_key


def _headers(secret, tenant, subject, roles):
    token=mint_pilot_key(secret,tenant,roles,1,subject)
    return {"Authorization":"Bearer "+token,"x-eurosetu-tenant":tenant}


def test_synthetic_pdf_to_audited_ready(monkeypatch,tmp_path):
    monkeypatch.setattr(db,"DB_PATH",tmp_path/"pilot.db")
    monkeypatch.setenv("EUROSETU_JWT_SECRET","dossier-test-secret")
    contributor=_headers("dossier-test-secret","tenant-a","contributor@example.test",["pilot_contributor"])
    verifier=_headers("dossier-test-secret","tenant-a","verifier@example.test",["verifier"])
    other=_headers("dossier-test-secret","tenant-b","other@example.test",["pilot_viewer"])
    with TestClient(app) as client:
        created=client.post("/api/dossiers/demo",headers=contributor)
        assert created.status_code==201,created.text
        state=created.json();dossier_id=state["dossier"]["id"]
        assert state["decision"]=="BLOCKED"
        assert {b["code"] for b in state["blockers"]}>={"HEAT_MISMATCH","CBAM_VERIFICATION_MISSING"}
        assert state["calculation"]["specific_embedded_emissions_tco2_per_t"]==1.55
        assert state["calculation"]["shipment_embedded_emissions_tco2"]==3.4906
        assert client.get(f"/api/dossiers/{dossier_id}",headers=other).status_code==404
        assert client.get(f"/api/dossiers/{dossier_id}").status_code==401
        assert client.get("/dossier-demo").status_code==200
        for role,document_id in state["active_document_ids"].items():
            pdf=client.get(f"/api/dossiers/{dossier_id}/documents/{document_id}/pdf",headers=verifier)
            assert pdf.status_code==200 and b"SYNTHETIC DEMONSTRATION" in pdf.content
            doc=next(d for d in state["documents"] if d["id"]==document_id)
            assert hashlib.sha256(pdf.content).hexdigest()==doc["sha256"]
            reviewed=client.post(f"/api/dossiers/{dossier_id}/documents/{document_id}/review",
                                 json={"approve":True,"reason":"Source and parsed facts inspected"},headers=verifier)
            assert reviewed.status_code==200,reviewed.text
            state=reviewed.json()
        assert state["decision"]=="BLOCKED"
        assert {b["code"] for b in state["blockers"]}=={"HEAT_MISMATCH","CBAM_VERIFICATION_MISSING"}
        for role in ("MTC","CBAM_INSTALLATION"):
            replaced=client.post(f"/api/dossiers/{dossier_id}/remediate/{role}",headers=contributor)
            assert replaced.status_code==200,replaced.text
            state=replaced.json()
            assert state["decision"]=="BLOCKED"
            document_id=state["active_document_ids"][role]
            own_review=client.post(f"/api/dossiers/{dossier_id}/documents/{document_id}/review",
                                   json={"approve":True,"reason":"self"},headers=contributor)
            assert own_review.status_code==403
            state=client.post(f"/api/dossiers/{dossier_id}/documents/{document_id}/review",
                              json={"approve":True,"reason":"Corrected source inspected"},headers=verifier).json()
        assert state["decision"]=="READY"
        assert not state["blockers"]
        assert state["calculation"]["status"]=="CALCULATED_VERIFIED"
        assert len(state["evidence_graph"]["edges"])==6
        assert len(state["events"])==31
        transitions=[e["payload"]["status"] for e in state["events"] if e["kind"]=="decision.evaluated"]
        assert transitions[0]=="BLOCKED" and transitions[-1]=="READY"
        assert state["integrity"]=={"source_pdfs":True,"audit_chain":True,"decision_snapshot":True}
        previous=None
        for event in state["events"]:
            assert event["previous_hash"]==previous
            canonical=json.dumps({"dossier_id":dossier_id,"actor":event["actor"],"kind":event["kind"],
                                  "payload":event["payload"],"previous_hash":previous,"created_at":event["created_at"]},
                                 sort_keys=True,separators=(",",":"))
            assert hashlib.sha256(canonical.encode()).hexdigest()==event["event_hash"]
            previous=event["event_hash"]


def test_reviewer_cannot_approve_own_document(monkeypatch,tmp_path):
    monkeypatch.setattr(db,"DB_PATH",tmp_path/"pilot.db")
    monkeypatch.setenv("EUROSETU_JWT_SECRET","dossier-test-secret")
    admin=_headers("dossier-test-secret","tenant-a","admin@example.test",["admin","verifier"])
    with TestClient(app) as client:
        state=client.post("/api/dossiers/demo",headers=admin).json()
        dossier_id=state["dossier"]["id"]
        document_id=state["active_document_ids"]["INVOICE"]
        response=client.post(f"/api/dossiers/{dossier_id}/documents/{document_id}/review",
                             json={"approve":True,"reason":"own document"},headers=admin)
        assert response.status_code==409
        assert response.json()["detail"]=="REVIEWER_MUST_DIFFER_FROM_SUBMITTER"


def test_source_tampering_blocks_and_cannot_be_reviewed(monkeypatch,tmp_path):
    monkeypatch.setattr(db,"DB_PATH",tmp_path/"pilot.db")
    monkeypatch.setenv("EUROSETU_JWT_SECRET","dossier-test-secret")
    contributor=_headers("dossier-test-secret","tenant-a","contributor@example.test",["pilot_contributor"])
    verifier=_headers("dossier-test-secret","tenant-a","verifier@example.test",["verifier"])
    with TestClient(app) as client:
        state=client.post("/api/dossiers/demo",headers=contributor).json()
        dossier_id=state["dossier"]["id"]
        document_id=state["active_document_ids"]["INVOICE"]
        with db.connect() as conn:
            conn.execute("UPDATE pilot_dossier_documents SET facts_json=? WHERE id=?",
                         (json.dumps({"document_type":"INVOICE","invoice_number":"FORGED"}),document_id))
        state=client.get(f"/api/dossiers/{dossier_id}",headers=contributor).json()
        assert state["decision"]=="BLOCKED"
        assert state["integrity"]["source_pdfs"] is False
        assert "SOURCE_INTEGRITY_FAILED" in {b["code"] for b in state["blockers"]}
        review=client.post(f"/api/dossiers/{dossier_id}/documents/{document_id}/review",
                           json={"approve":True,"reason":"looks okay"},headers=verifier)
        assert review.status_code==409
        assert review.json()["detail"]=="PARSED_SOURCE_MISMATCH"


def test_ready_requires_identifiers_rows_and_customs_value(monkeypatch,tmp_path):
    from app.pilot_dossier import _assess, _parse_pdf, FIXTURES, INITIAL
    active={}
    for role,filename in INITIAL.items():
        facts,rows,_=_parse_pdf((FIXTURES/filename).read_bytes())
        active[role]={"id":role,"facts":facts,"rows":rows,"review_status":"APPROVED"}
    active["MTC"]["facts"]["heat_number"]=active["INVOICE"]["facts"]["heat_number"]
    active["CBAM_INSTALLATION"]["facts"]["verifier_status"]="VERIFIED"
    active["CBAM_INSTALLATION"]["facts"]["verifier_report_ref"]="DEMO-VERIFY-001"
    active["INVOICE"]["facts"].pop("origin_country")
    active["SAD"]["rows"]=[]
    active["SAD"]["facts"]["customs_value_eur"]="45001.00"
    blockers,_,_=_assess(active)
    codes={b["code"] for b in blockers}
    assert {"REQUIRED_FIELD_MISSING","ITEM_ROWS_MISSING","CUSTOMS_VALUE_MISMATCH"}<=codes


def test_pdf_download_rejects_tampered_bytes(monkeypatch,tmp_path):
    monkeypatch.setattr(db,"DB_PATH",tmp_path/"pilot.db")
    monkeypatch.setenv("EUROSETU_JWT_SECRET","dossier-test-secret")
    contributor=_headers("dossier-test-secret","tenant-a","contributor@example.test",["pilot_contributor"])
    with TestClient(app) as client:
        state=client.post("/api/dossiers/demo",headers=contributor).json()
        dossier_id=state["dossier"]["id"]
        document_id=state["active_document_ids"]["INVOICE"]
        with db.connect() as conn:
            conn.execute("UPDATE pilot_dossier_documents SET pdf=? WHERE id=?",(b"%PDF-corrupt",document_id))
        response=client.get(f"/api/dossiers/{dossier_id}/documents/{document_id}/pdf",headers=contributor)
        assert response.status_code==409
        assert response.json()["detail"]=="SOURCE_INTEGRITY_FAILED"
