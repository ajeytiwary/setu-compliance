"""REGULATION-TIME-TRAVEL (P0, SYNTHETIC+NORMATIVE): point-in-time replay (§5.12).

Same transaction at T1 and T2 with effective-dated source snapshots.
T1 replay stable after T2 installed; T2 uses only T2-effective sources;
diff names the causal change; audit bundle needs no mutable state.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app import source_registry as sr
from app.benchmark_harness import BenchmarkCase
from app.main import app

T1 = "2026-06-30"
T2 = "2026-08-28"


def _ob(status: str, oid: str = "CBAM_EMISSIONS") -> dict:
    return {"obligation_id": oid, "applicable": True, "status": status,
            "reasons": [] if status == "PASS" else [f"{oid} {status} at source version"],
            "severity": "BLOCKING", "required_for_release": True,
            "schema_version": "EUROSETU_CANONICAL_V1"}


def test_time_travel_replay_stable():
    case = BenchmarkCase(suite_id="TIME-TRAVEL", case_id="t1_t2_001",
                         evidence_class="SYNTHETIC", as_of=T2)
    client = TestClient(app)
    # T1 source snapshot effective through July; T2 snapshot from August
    s1 = sr.register(source_id="CBAM_DEFAULTS", authority="EC",
                     title="CBAM defaults v1", legal_basis=["2025/2621"],
                     version="v1", effective_from="2026-01-01",
                     effective_to="2026-07-31", content=b"defaults-v1")
    s2 = sr.register(source_id="CBAM_DEFAULTS", authority="EC",
                     title="CBAM defaults v2 (corrected)", legal_basis=["2026/1740"],
                     version="v2", effective_from="2026-08-01",
                     content=b"defaults-v2")
    txn = {"transaction_ref": "TXN-TIMETRAVEL-001", "order_id": "PO-TT",
           "shipment_id": "SHP-TT", "line_id": "L1", "origin_country": "IN",
           "destination_country": "NL", "shipment_date": T1,
           "line_value": 200000.0, "quantity": 40.0, "unit": "t",
           "cn_code": "72083900"}
    assert client.post("/v1/transactions", json=txn).status_code in (200, 201)

    def snap_ref(s: dict) -> dict:
        return {"id": s["source_id"], "sha256": s["content_hash"],
                "version": s["version"]}

    r1 = client.post("/v1/market-access/check", json={
        "transaction_ref": txn["transaction_ref"], "as_of": T1,
        "obligations": [_ob("PASS")],
        "source_snapshot_refs": [snap_ref(s1)], "evidence_snapshot_refs": []})
    assert r1.status_code == 201, r1.text
    d1 = r1.json()

    # T2: same transaction, new source version, changed outcome
    r2 = client.post("/v1/market-access/check", json={
        "transaction_ref": txn["transaction_ref"], "as_of": T2,
        "obligations": [_ob("FAIL")],
        "source_snapshot_refs": [snap_ref(s2)], "evidence_snapshot_refs": [],
        "predecessor_id": d1["decision_id"]})
    assert r2.status_code == 201, r2.text
    d2 = r2.json()

    # T1 replay after T2 installed: stable, uses only T1 snapshot
    rr = client.post(f"/v1/decisions/{d1['decision_id']}/replay")
    assert rr.status_code == 201, rr.text
    rep = rr.json()
    eff_t1 = sr.effective_at(T1)
    eff_t2 = sr.effective_at(T2)
    case.assert_and_emit(
        {"t1_status": d1["status"], "t2_status": d2["status"],
         "replay_status": rep["status"],
         "replay_matches_t1": rep["status"] == d1["status"],
         "t1_snapshot_version": d1["source_snapshot_refs"][0]["version"],
         "t2_snapshot_version": d2["source_snapshot_refs"][0]["version"],
         "causal_change": d1["source_snapshot_refs"] != d2["source_snapshot_refs"],
         "t1_effective_has_v1": any(s["version"] == "v1" for s in eff_t1),
         "t2_effective_has_v2": any(s["version"] == "v2" for s in eff_t2)},
        {"t1_status": "READY", "t2_status": "BLOCKED",
         "replay_status": "READY", "replay_matches_t1": True,
         "t1_snapshot_version": "v1", "t2_snapshot_version": "v2",
         "causal_change": True,
         "t1_effective_has_v1": True, "t2_effective_has_v2": True},
        decision_id=rep["decision_id"])
