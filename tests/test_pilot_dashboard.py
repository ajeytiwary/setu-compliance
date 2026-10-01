"""Pilot dashboard regression tests.

The pilot dashboard (/pilot) is separate from the customer-facing website
(/) and the public demo (/demo). These tests guard the route registration,
the 12-week plan shape, the six data contracts, and the overview payload.
"""
from app.pilot import DATA_CONTRACTS, PILOT_WEEKS, pilot_overview\nimport base64,hashlib,hmac,json,time\n\ndef _auth(monkeypatch,roles=("pilot_contributor","verifier"),tenant="tenant-a"):\n    secret="test-secret"; monkeypatch.setenv("EUROSETU_JWT_SECRET",secret)\n    enc=lambda o:base64.urlsafe_b64encode(json.dumps(o,separators=(",",":")).encode()).rstrip(b"=").decode()\n    h=enc({"alg":"HS256","typ":"JWT"}); p=enc({"sub":"test-user","exp":int(time.time())+3600,"tenant_id":tenant,"tenants":{tenant:list(roles)}})\n    sig=base64.urlsafe_b64encode(hmac.new(secret.encode(),f"{h}.{p}".encode(),hashlib.sha256).digest()).rstrip(b"=").decode()\n    return {"Authorization":f"Bearer {h}.{p}.{sig}","x-eurosetu-tenant":tenant}


def test_pilot_plan_and_contracts_shape():
    assert [w["week"] for w in PILOT_WEEKS] == list(range(1, 13))
    assert len(DATA_CONTRACTS) == 6
    assert {c["id"] for c in DATA_CONTRACTS} == {
        "sap_sd", "sap_mm", "mes", "ems", "supplier_cbam", "verifier"}
    for w in PILOT_WEEKS:
        assert w["objective"] and w["exit"] and w["signal"]


def test_pilot_overview_shape():
    d = pilot_overview()
    for key in ("scope", "kpis", "weeks", "contracts", "shipments",
                "cbam_calculations", "remediation", "regulatory", "audit",
                "risk"):
        assert key in d, key
    assert len(d["weeks"]) == 12
    assert len(d["contracts"]) == 6
    assert all(w["status"] in ("SIGNAL_PRESENT", "NO_SIGNAL", "MANUAL_TRACKING")
               for w in d["weeks"])
    assert all(c["status"] in ("CONNECTED_ROWS", "NO_ROWS") for c in d["contracts"])
    assert "READY_FOR_SUBMISSION" in d["scope"]["notice"]
    assert d["kpis"]["shipments"] == len(d["shipments"])
    # Risk drilldown drives the "Where is the money blocked?" panel.
    for key in ("metrics", "countries", "rule_risk", "drilldown"):
        assert key in d["risk"], key
    assert "eu_order_book_eur" in d["risk"]["metrics"]


def test_pilot_routes_registered():
    from app.main import app
    paths = {getattr(r, "path", None) for r in app.routes}
    assert "/pilot" in paths
    assert "/pilot.js" in paths
    assert "/api/pilot/overview" in paths
    assert "/api/pilot/shipments/{shipment_id}/simulate-remediation" in paths
    assert "/api/pilot/remediation/requests" in paths
    assert "/api/pilot/suppliers/{supplier_id}/evidence" in paths
    assert "/api/pilot/evidence/{evidence_id}/verify" in paths
    assert "/api/pilot/remediation/requests/{request_id}/resolve" in paths


def test_pilot_evidence_cycle_end_to_end(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.db import init_db, connect, row
    from app.rules import STEEL_EU_RULES
    from uuid import uuid4
    init_db()
    client = TestClient(app)\n    headers=_auth(monkeypatch)
    sid, sup = str(uuid4()), str(uuid4())
    now = "2026-09-29T00:00:00+00:00"
    with connect() as c:
        c.execute("INSERT INTO shipments(id,shipment_no,exporter,facility,importer,destination_country,product,cn_code,tonnes,value_eur,emissions_method,supplier_required,supplier_complete,manual_hours,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  (sid, "PILOT-E2E-" + sid[:6], "Exporter", "Plant", "Importer", "NL", "HRC", "7208", 10, 300000, "actual", 0, 0, 0, now, now))
        for r in STEEL_EU_RULES:
            c.execute("INSERT INTO requirements(shipment_id,code,label,category,blocking,status,required_evidence,evidence_count) VALUES(?,?,?,?,?,?,?,0)",
                      (sid, r.code, r.label, r.category, int(r.blocking), "PASS" if r.code != "SUPPLIER_DATA" else "MISSING", r.required_evidence))
        c.execute("INSERT INTO suppliers(id,name,facility,country,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                  (sup, "E2E Supplier", "Plant", "IN", "ACTIVE", now, now))
        c.execute("INSERT INTO supplier_shipment_links(id,supplier_id,shipment_id,material,quantity_t,required_evidence_type,created_at) VALUES(?,?,?,?,?,?,?)",
                  (str(uuid4()), sup, sid, "ferroalloy", 1, "CBAM_PRECURSOR", now))
    sim = client.post(f"/api/pilot/shipments/{sid}/simulate-remediation",
                      json={"requirement_code": "SUPPLIER_DATA", "estimated_cost_eur": 2000})
    assert sim.status_code == 200
    assert sim.json()["proposed_solution"]["requirement_code"] == "SUPPLIER_DATA"
    assert sim.json()["after"]["market_ready"] is True
    req = client.post("/api/pilot/remediation/requests", headers=headers, json={
        "shipment_id": sid, "supplier_id": sup, "requirement_code": "SUPPLIER_DATA",
        "evidence_type": "CBAM_PRECURSOR", "owner": "Procurement"})
    assert req.status_code == 201
    req_id = req.json()["id"]
    sub = client.post(f"/api/pilot/suppliers/{sup}/evidence", headers=headers, json={
        "evidence_type": "CBAM_PRECURSOR", "content": "e2e-precursor-file"})
    assert sub.status_code == 201
    ev_id = sub.json()["id"]
    assert sub.json()["status"] == "PENDING"
    ver = client.post(f"/api/pilot/evidence/{ev_id}/verify", headers=headers, json={"verifier": "Accredited verifier"})
    assert ver.status_code == 200
    assert ver.json()["status"] == "VERIFIED"
    res = client.post(f"/api/pilot/remediation/requests/{req_id}/resolve", headers=headers, json={"evidence_id": ev_id})
    assert res.status_code == 200
    assert res.json()["status"] == "RESOLVED"
    with connect() as c:
        assert row(c, "SELECT status FROM requirements WHERE shipment_id=? AND code='SUPPLIER_DATA'", (sid,))["status"] == "PASS"
