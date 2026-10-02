"""EVIDENCE-DECAY (P0, SYNTHETIC): 7-state lifecycle + invalidation (§5.11).

Deterministic as_of clock; freshness policy separate from legal validity.
Each transition → expected obligation/decision transition; conflicts surface
(no last-write-wins); superseded stays historical; recomputation incremental.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app import evidence_lifecycle as ev
from app.benchmark_harness import BenchmarkCase
from app.main import app

AS_OF = "2026-08-28"


def _ev(**over) -> dict:
    base = {"evidence_id": "E1", "subject_ref": "SHP-DECAY",
            "collected_at": "2026-08-01",
            "verification_status": "VERIFIED"}
    base.update(over)
    return base


def test_evidence_decay_all_states():
    case = BenchmarkCase(suite_id="EVIDENCE-DECAY", case_id="states_001",
                         evidence_class="SYNTHETIC", as_of=AS_OF)
    actual = {
        "valid": ev.classify(_ev(), as_of=AS_OF),
        "stale": ev.classify(_ev(collected_at="2024-01-01"), as_of=AS_OF,
                             freshness_days=365),
        "expired": ev.classify(_ev(valid_to="2026-01-01"), as_of=AS_OF),
        "superseded": ev.classify(_ev(superseded_by="E2"), as_of=AS_OF),
        "conflicting": ev.classify(_ev(conflicting=True), as_of=AS_OF),
        "unverified": ev.classify(_ev(verification_status="PENDING"), as_of=AS_OF),
        "missing": ev.evaluate_requirement([], as_of=AS_OF)["state"],
    }
    case.assert_and_emit(actual, {
        "valid": "VALID", "stale": "STALE", "expired": "EXPIRED",
        "superseded": "SUPERSEDED", "conflicting": "CONFLICTING",
        "unverified": "UNVERIFIED", "missing": "MISSING"})


def test_evidence_decay_conflict_not_last_write():
    """Two active objects disagreeing → CONFLICTING, usable empty (§5.11)."""
    case = BenchmarkCase(suite_id="EVIDENCE-DECAY", case_id="conflict_001",
                         evidence_class="SYNTHETIC", as_of=AS_OF)
    a = _ev(evidence_id="EA", content_hash="aaa",
            verification_status="VERIFIED", collected_at="2026-08-01")
    b = _ev(evidence_id="EB", content_hash="bbb",
            verification_status="VERIFIED", collected_at="2026-08-02")
    out = ev.evaluate_requirement([a, b], as_of=AS_OF)
    case.assert_and_emit(
        {"state": out["state"], "usable": out["usable"]},
        {"state": "CONFLICTING", "usable": []})


def test_evidence_decay_propagates_to_decision():
    """STALE evidence on a blocking obligation → decision not READY."""
    case = BenchmarkCase(suite_id="EVIDENCE-DECAY", case_id="propagation_001",
                         evidence_class="SYNTHETIC", as_of=AS_OF)
    client = TestClient(app)
    txn = {"transaction_ref": "TXN-DECAY-001", "order_id": "PO-DECAY",
           "shipment_id": "SHP-DECAY", "line_id": "L1", "origin_country": "IN",
           "destination_country": "NL", "shipment_date": AS_OF,
           "line_value": 100000.0, "quantity": 20.0, "unit": "t",
           "cn_code": "72083900"}
    assert client.post("/v1/transactions", json=txn).status_code in (200, 201)
    stale_ob = {"obligation_id": "CBAM_EMISSIONS", "applicable": True,
                "status": "STALE",
                "reasons": ["installation evidence older than freshness policy"],
                "severity": "BLOCKING", "required_for_release": True,
                "schema_version": "EUROSETU_CANONICAL_V1"}
    r = client.post("/v1/market-access/check", json={
        "transaction_ref": txn["transaction_ref"], "as_of": AS_OF,
        "obligations": [stale_ob],
        "source_snapshot_refs": [], "evidence_snapshot_refs": ["E-STALE-001"]})
    assert r.status_code == 201, r.text
    d = r.json()
    case.assert_and_emit(
        {"status": d["status"], "not_ready": d["status"] != "READY"},
        {"status": "BLOCKED", "not_ready": True},
        decision_id=d["decision_id"])
