"""SAP-BLOCK (P0, COMPETITIVE-SCENARIO): SAP-GTS-like gating + recompile (§5.5).

Fixture PO EU-000342. Initial: CBAM/origin/TARIC pass, quota freshness fails
→ CONDITIONAL/BLOCKED, never READY. Remediation + refreshed snapshot +
recompile → READY. First decision immutable, linked as predecessor.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.benchmark_harness import BenchmarkCase
from app.main import app

AS_OF = "2026-08-28"


def _pass(obligation_id: str) -> dict:
    return {"obligation_id": obligation_id, "applicable": True, "status": "PASS",
            "reasons": [], "severity": "BLOCKING", "required_for_release": True,
            "schema_version": "EUROSETU_CANONICAL_V1"}


def _stale_quota() -> dict:
    return {"obligation_id": "TARIFF_QUOTA", "applicable": True, "status": "STALE",
            "reasons": ["quota balance snapshot older than freshness policy"],
            "severity": "BLOCKING", "required_for_release": True,
            "schema_version": "EUROSETU_CANONICAL_V1"}


def test_sap_block_initial_not_ready():
    case = BenchmarkCase(suite_id="SAP-BLOCK", case_id="initial_001",
                         evidence_class="COMPETITIVE-SCENARIO", as_of=AS_OF)
    client = TestClient(app)
    txn = {"transaction_ref": "TXN-SAPBLOCK-001", "order_id": "PO-EU-000342",
           "shipment_id": "SHP-SAP", "line_id": "L1", "origin_country": "IN",
           "destination_country": "DE", "shipment_date": AS_OF,
           "line_value": 250000.0, "quantity": 50.0, "unit": "t",
           "cn_code": "72083900"}
    assert client.post("/v1/transactions", json=txn).status_code in (200, 201)
    r = client.post("/v1/market-access/check", json={
        "transaction_ref": txn["transaction_ref"], "as_of": AS_OF,
        "obligations": [_pass("SANCTIONS"), _pass("CBAM_EMISSIONS"),
                        _pass("ORIGIN"), _pass("TARIC_DUTY"), _stale_quota()],
        "source_snapshot_refs": [], "evidence_snapshot_refs": []})
    assert r.status_code == 201, r.text
    d1 = r.json()
    case.assert_and_emit(
        {"status": d1["status"], "not_ready": d1["status"] != "READY",
         "names_quota": any("TARIFF_QUOTA" in b for b in d1["blocking_reasons"])},
        {"status": "BLOCKED", "not_ready": True, "names_quota": True},
        decision_id=d1["decision_id"])
    # stash predecessor for the recompile test via the decision API
    test_sap_block_initial_not_ready.decision_id = d1["decision_id"]


def test_sap_block_recompile_ready_with_predecessor():
    case = BenchmarkCase(suite_id="SAP-BLOCK", case_id="recompile_001",
                         evidence_class="COMPETITIVE-SCENARIO", as_of=AS_OF)
    client = TestClient(app)
    txn = {"transaction_ref": "TXN-SAPBLOCK-002", "order_id": "PO-EU-000342",
           "shipment_id": "SHP-SAP", "line_id": "L1", "origin_country": "IN",
           "destination_country": "DE", "shipment_date": AS_OF,
           "line_value": 250000.0, "quantity": 50.0, "unit": "t",
           "cn_code": "72083900"}
    assert client.post("/v1/transactions", json=txn).status_code in (200, 201)
    r1 = client.post("/v1/market-access/check", json={
        "transaction_ref": txn["transaction_ref"], "as_of": AS_OF,
        "obligations": [_pass("SANCTIONS"), _pass("CBAM_EMISSIONS"),
                        _pass("ORIGIN"), _pass("TARIC_DUTY"), _stale_quota()],
        "source_snapshot_refs": [], "evidence_snapshot_refs": []})
    d1 = r1.json()
    assert d1["status"] == "BLOCKED"
    # remediation: refreshed quota snapshot → quota check now passes
    r2 = client.post("/v1/market-access/check", json={
        "transaction_ref": txn["transaction_ref"], "as_of": AS_OF,
        "obligations": [_pass("SANCTIONS"), _pass("CBAM_EMISSIONS"),
                        _pass("ORIGIN"), _pass("TARIC_DUTY"),
                        _pass("TARIFF_QUOTA")],
        "source_snapshot_refs": [{"id": "quota-snapshot-2026-08-28",
                                  "sha256": "refreshed", "version": "v2"}],
        "evidence_snapshot_refs": [], "predecessor_id": d1["decision_id"]})
    assert r2.status_code == 201, r2.text
    d2 = r2.json()
    # predecessor immutable: still BLOCKED when re-fetched
    orig = client.get(f"/v1/decisions/{d1['decision_id']}").json()
    case.assert_and_emit(
        {"second_status": d2["status"],
         "predecessor_linked": d2.get("predecessor_id") == d1["decision_id"],
         "predecessor_still_blocked": orig["status"] == "BLOCKED"},
        {"second_status": "READY",
         "predecessor_linked": True, "predecessor_still_blocked": True},
        decision_id=d2["decision_id"])
