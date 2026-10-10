from fastapi.testclient import TestClient

from app.main import app
from app.pilot_keys import mint_pilot_key
from app.regulatory_feed import add_watch, events, publish_change, review_event


def measure(cn, origin, duty, start="2026-10-01"):
    return {"cn_code": cn, "origin_country": origin, "measure_type": "103",
            "duty_rate": duty, "valid_from": start, "legal_basis": "TEST-REG"}


def test_taric_row_diff_is_scoped_traceable_and_idempotent():
    add_watch("tenant-a", "72083900", "IN")
    add_watch("tenant-b", "72221119", "IN")
    old = [measure("7208390010", "IN", "5%"), measure("7222111900", "IN", "2%")]
    new = [measure("7208390010", "IN", "7%"), measure("7222111900", "IN", "2%")]
    result = publish_change("taric_measures", "sha-old", "sha-new", old, new,
                            "https://example.test/taric", "2026-10-07")
    assert result["events"] == 1
    assert publish_change("taric_measures", "sha-old", "sha-new", old, new,
                          "https://example.test/taric", "2026-10-07")["events"] == 0
    event = events("tenant-a")[0]
    assert event["change_type"] == "UPDATED"
    assert event["old_record"]["duty_rate"] == "5%"
    assert event["new_record"]["duty_rate"] == "7%"
    assert (event["old_sha"], event["new_sha"], event["source_url"]) == (
        "sha-old", "sha-new", "https://example.test/taric")
    assert events("tenant-b") == []
    assert events("tenant-a", as_of="2026-09-30") == []


def test_unknown_dataset_and_baseline_do_not_claim_product_impact():
    add_watch("tenant-a", "72083900", "IN")
    rows = [measure("7208390010", "IN", "7%")]
    assert publish_change("eucdm", "a", "b", rows, rows, "url", "2026-10-07")["status"] == "UNSUPPORTED_DATASET"
    assert publish_change("taric_measures", None, "b", None, rows, "url", "2026-10-07")["status"] == "BASELINE_CREATED"
    assert events("tenant-a") == []


def test_feed_api_requires_role_and_isolates_tenants(monkeypatch):
    monkeypatch.setenv("EUROSETU_JWT_SECRET", "feed-test")
    client = TestClient(app)
    def headers(tenant, role):
        token = mint_pilot_key("feed-test", tenant, [role], 1, "user@example.test")
        return {"authorization": "Bearer " + token, "x-eurosetu-tenant": tenant}
    a = headers("tenant-a", "pilot_contributor")
    b = headers("tenant-b", "pilot_viewer")
    assert client.get("/api/regulatory-feed/events").status_code == 401
    assert client.post("/api/regulatory-feed/watches", headers=b,
                       json={"cn_code": "72083900", "origin_country": "IN"}).status_code == 403
    created = client.post("/api/regulatory-feed/watches", headers=a,
                          json={"cn_code": "72083900", "origin_country": "IN"})
    assert created.status_code == 200
    assert client.get("/api/regulatory-feed/watches", headers=b).json()["watches"] == []
    publish_change("taric_measures", "old", "new", [measure("7208390010", "IN", "5%")],
                   [measure("7208390010", "IN", "7%")], "https://example.test", "2026-10-07")
    assert len(client.get("/api/regulatory-feed/events", headers=a).json()["events"]) == 1
    assert client.get("/api/regulatory-feed/events", headers=b).json()["events"] == []
    assert client.get("/api/regulatory-feed/events.csv", headers=a).status_code == 200


def test_future_effective_row_is_recorded_and_visible_as_of_date():
    add_watch("tenant-a", "72083900", "IN")
    new = [measure("7208390010", "IN", "8%", start="2026-11-01")]
    result = publish_change("taric_measures", "old", "new", [], new,
                            "https://example.test/future", "2026-10-07")
    assert result["events"] == 1
    assert events("tenant-a", as_of="2026-10-07") == []
    assert len(events("tenant-a", as_of="2026-11-01")) == 1


def test_review_is_append_only_and_tenant_scoped():
    add_watch("tenant-a", "72083900", "IN")
    publish_change("taric_measures", "old", "new", [measure("7208390010", "IN", "5%")],
                   [measure("7208390010", "IN", "7%")], "https://example.test", "2026-10-07")
    event_id = events("tenant-a")[0]["id"]
    import pytest
    with pytest.raises(KeyError):
        review_event("tenant-b", event_id, "other@example.test", "DISMISSED", "Wrong tenant review")
    review_event("tenant-a", event_id, "reviewer@example.test", "ESCALATED",
                 "Check the legal measure and document condition")
    assert events("tenant-a")[0]["review"]["disposition"] == "ESCALATED"
    review_event("tenant-a", event_id, "reviewer@example.test", "ACKNOWLEDGED",
                 "Confirmed after checking official TARIC source")
    assert events("tenant-a")[0]["review"]["disposition"] == "ACKNOWLEDGED"
