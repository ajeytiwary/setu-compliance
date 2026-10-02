"""Shared helpers for benchmark suites: build transactions, run the v1 check path."""
from __future__ import annotations
import json
from fastapi.testclient import TestClient


def check(client: TestClient, txn: dict, as_of: str = "2026-08-28",
          obligations: list[dict] | None = None,
          cbam_payload: dict | None = None,
          taric_payload: dict | None = None,
          source_refs: list[dict] | None = None,
          predecessor_id: str | None = None) -> dict:
    ref = txn["transaction_ref"]
    r = client.post("/v1/transactions", json=txn)
    assert r.status_code in (200, 201), r.text
    body = {"transaction_ref": ref, "as_of": as_of,
            "obligations": obligations or [],
            "source_snapshot_refs": source_refs or [],
            "evidence_snapshot_refs": [],
            "predecessor_id": predecessor_id}
    if cbam_payload is not None:
        body["cbam_payload"] = cbam_payload
    if taric_payload is not None:
        body["taric_payload"] = taric_payload
    r = client.post("/v1/market-access/check", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def actual_from_decision(decision: dict) -> dict:
    by_id = {o["obligation_id"]: o for o in decision.get("obligation_results", [])}
    return {"status": decision.get("status"),
            "blocking_reasons": decision.get("blocking_reasons", []),
            "obligations": {k: v.get("status") for k, v in by_id.items()}}
