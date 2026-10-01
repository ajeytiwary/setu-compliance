"""Manual pilot-key issuance: shared minter + admin queue.

Guards:
- mint_pilot_key parity vector (Python side of the Worker contract).
- /api/admin/requests + /api/admin/mint are admin-gated (401/403 without).
- Minted key actually unlocks /api/pilot/overview (end-to-end manual flow).
- /admin page serves the founder queue UI.
"""
import base64
import hashlib
import hmac
import json
import time

from fastapi.testclient import TestClient

from app.main import app
from app.pilot_keys import mint_pilot_key


def _admin_headers(monkeypatch, tenant="tenant-a"):
    monkeypatch.setenv("EUROSETU_JWT_SECRET", "test-secret")
    token = mint_pilot_key("test-secret", tenant, ["admin"], 30, "founder@eurosetu.trade")
    return {"Authorization": f"Bearer {token}", "x-eurosetu-tenant": tenant}


def test_mint_parity_vector():
    # Fixed vector: the Cloudflare Worker must produce this exact token for
    # the same inputs (secret "s", now=1700000000). If this test changes, the
    # Worker contract in workers/pilot-key-minter.js must change with it.
    token = mint_pilot_key("s", "tenant-a", ["pilot_viewer"], 30, "a@b.co", now=1700000000)
    h, p, s = token.split(".")
    claims = json.loads(base64.urlsafe_b64decode(p + "=" * (-len(p) % 4)))
    assert claims == {
        "sub": "a@b.co",
        "exp": 1700000000 + 30 * 86400,
        "iat": 1700000000,
        "tenant_id": "tenant-a",
        "tenants": {"tenant-a": ["pilot_viewer"]},
    }
    expected_sig = base64.urlsafe_b64encode(
        hmac.new(b"s", f"{h}.{p}".encode(), hashlib.sha256).digest()
    ).rstrip(b"=").decode()
    assert s == expected_sig


def test_mint_rejects_bad_input():
    for kwargs in (
        {"secret": "", "tenant": "t", "roles": ["pilot_viewer"], "days": 30, "sub": "a@b.co"},
        {"secret": "s", "tenant": "", "roles": ["pilot_viewer"], "days": 30, "sub": "a@b.co"},
        {"secret": "s", "tenant": "t", "roles": [], "days": 30, "sub": "a@b.co"},
        {"secret": "s", "tenant": "t", "roles": ["pilot_viewer"], "days": 0, "sub": "a@b.co"},
        {"secret": "s", "tenant": "t", "roles": ["pilot_viewer"], "days": 30, "sub": "not-an-email"},
    ):
        try:
            mint_pilot_key(**kwargs)
        except ValueError:
            continue
        raise AssertionError(f"should have rejected {kwargs}")


def test_admin_queue_requires_admin(monkeypatch):
    c = TestClient(app)
    assert c.get("/api/admin/requests").status_code == 401
    assert c.post("/api/admin/mint", json={"email": "a@b.co"}).status_code == 401
    # Non-admin pilot key cannot list or mint.
    monkeypatch.setenv("EUROSETU_JWT_SECRET", "test-secret")
    viewer = mint_pilot_key("test-secret", "tenant-a", ["pilot_viewer"], 30, "v@x.co")
    h = {"Authorization": f"Bearer {viewer}", "x-eurosetu-tenant": "tenant-a"}
    assert c.get("/api/admin/requests", headers=h).status_code == 403
    assert c.post("/api/admin/mint", headers=h, json={"email": "a@b.co"}).status_code == 403


def test_admin_mint_unlocks_pilot_end_to_end(monkeypatch):
    c = TestClient(app)
    h = _admin_headers(monkeypatch)
    # Seed a contact enquiry like the public form does.
    c.post("/api/contact", json={"name": "Priya", "work_email": "priya@company.com", "company": "Acme"})
    q = c.get("/api/admin/requests", headers=h)
    assert q.status_code == 200
    assert any(r["work_email"] == "priya@company.com" for r in q.json()["contacts"])
    # Founder mints with defaults (tenant/roles/days omitted).
    m = c.post("/api/admin/mint", headers=h, json={"email": "priya@company.com"})
    assert m.status_code == 201
    body = m.json()
    assert body["email"] == "priya@company.com" and body["token"].count(".") == 2
    # The manually-sent key unlocks the pilot API.
    pilot = c.get(
        "/api/pilot/overview",
        headers={"Authorization": f"Bearer {body['token']}", "x-eurosetu-tenant": body["tenant"]},
    )
    assert pilot.status_code == 200


def test_admin_page_serves_queue_ui():
    c = TestClient(app)
    r = c.get("/admin")
    assert r.status_code == 200
    assert "Pilot key queue" in r.text
    assert "Mint key" in r.text
