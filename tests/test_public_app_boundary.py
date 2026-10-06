from fastapi.testclient import TestClient
from app.main import app


def test_split_host_rejects_wrong_host_and_public_pages(monkeypatch):
    monkeypatch.setenv("EUROSETU_ENV", "production")
    monkeypatch.setenv("EUROSETU_SPLIT_HOSTS", "1")
    monkeypatch.setenv("EUROSETU_APP_HOST", "app.eurosetu.trade")
    monkeypatch.setenv("EUROSETU_PUBLIC_PROXY_SECRET", "test-secret")
    client = TestClient(app)
    assert client.get("/pilot", headers={"host": "eurosetu.trade"}).status_code == 421
    assert client.get("/pilot", headers={"host": "app.eurosetu.trade"}).status_code == 200
    assert client.get("/trust", headers={"host": "app.eurosetu.trade"}).status_code == 404
    assert client.get("/", headers={"host": "app.eurosetu.trade"}, follow_redirects=False).headers["location"] == "/pilot"


def test_public_proxy_requires_secret(monkeypatch):
    monkeypatch.setenv("EUROSETU_ENV", "production")
    monkeypatch.setenv("EUROSETU_SPLIT_HOSTS", "1")
    monkeypatch.setenv("EUROSETU_APP_HOST", "app.eurosetu.trade")
    monkeypatch.setenv("EUROSETU_PUBLIC_PROXY_SECRET", "test-secret")
    client = TestClient(app)
    path = "/api/tools/supplier-template.csv"
    assert client.get(path, headers={"host": "app.eurosetu.trade"}).status_code == 403
    assert client.get(path, headers={"host": "app.eurosetu.trade", "x-eurosetu-public-proxy-secret": "test-secret"}).status_code == 200
