"""Lead-gated demo: contact form -> token -> gated dashboard APIs."""
from fastapi.testclient import TestClient
from app.db import init_db
from app.main import app


def _client():
    init_db()
    return TestClient(app)


def test_lead_create_verify_and_gated_dashboard():
    c = _client()
    # gated without token
    r = c.get("/api/market-access/risk-drilldown")
    assert r.status_code == 403
    r = c.get("/api/dashboard")
    assert r.status_code == 403
    # invalid email rejected
    bad = c.post("/api/leads", json={"name": "X", "work_email": "not-an-email", "company": "Acme"})
    assert bad.status_code == 422
    # create lead
    ok = c.post("/api/leads", json={
        "name": "Priya Sharma", "work_email": "priya@example.com",
        "company": "JSW Steel", "role": "Exports", "message": "CBAM demo",
    })
    assert ok.status_code == 201, ok.text
    token = ok.json()["token"]
    assert token
    # verify
    v = c.get("/api/leads/verify", headers={"x-setu-lead-token": token})
    assert v.json()["valid"] is True
    # gated with token
    d = c.get("/api/market-access/risk-drilldown", headers={"x-setu-lead-token": token})
    assert d.status_code == 200, d.text
    assert "drilldown" in d.json()
    dash = c.get("/api/dashboard", headers={"x-setu-lead-token": token})
    assert dash.status_code == 200
    # returning lead reuses token
    again = c.post("/api/leads", json={
        "name": "Priya Sharma", "work_email": "priya@example.com", "company": "JSW Steel"})
    assert again.json()["token"] == token
    assert again.json()["returning"] is True


def test_demo_page_serves_gate():
    c = _client()
    r = c.get("/demo")
    assert r.status_code == 200
    assert "leadForm" in r.text
    assert "/demo.js" in r.text
