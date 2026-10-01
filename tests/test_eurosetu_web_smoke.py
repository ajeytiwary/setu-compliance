"""Public EuroSetu journey: landing page -> lead gate -> demo assets -> gated APIs."""
from fastapi.testclient import TestClient
from app.db import init_db
from app.main import app

def test_eurosetu_public_to_demo_journey():
    init_db()
    with TestClient(app) as c:
        home = c.get("/")
        assert home.status_code == 200
        assert "EuroSetu" in home.text
        assert 'href="/demo"' in home.text
        assert c.get("/public.css").status_code == 200
        trust = c.get("/trust")
        assert trust.status_code == 200 and "Trust & Security" in trust.text
        case = c.get("/case-study")
        assert case.status_code == 200 and "SYNTHETIC COMMERCIAL DATA" in case.text
        assert 'name="viewport"' in home.text
        assert 'name="viewport"' in trust.text
        assert 'name="viewport"' in case.text
        demo = c.get("/demo")
        assert demo.status_code == 200
        assert "leadForm" in demo.text
        assert c.get("/demo.js").status_code == 200
        assert c.get("/demo.css").status_code == 200
        assert c.get("/api/dashboard").status_code == 403
        created = c.post("/api/leads", json={
            "name": "EuroSetu E2E Smoke",
            "work_email": "smoke-eurosetu@example.com",
            "company": "Synthetic Example Co",
        })
        assert created.status_code == 201, created.text
        token = created.json()["token"]
        headers = {"x-eurosetu-lead-token": token}
        assert c.get("/api/leads/verify", headers=headers).json()["valid"] is True
        dashboard = c.get("/api/dashboard", headers=headers)
        assert dashboard.status_code == 200, dashboard.text
        risk = c.get("/api/market-access/risk-drilldown", headers=headers)
        assert risk.status_code == 200, risk.text
        assert "drilldown" in risk.json()
