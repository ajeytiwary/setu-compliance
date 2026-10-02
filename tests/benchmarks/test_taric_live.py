"""TARIC-LIVE (P0, SYNTHETIC): dated TARIC resolver regression using controlled snapshot fixtures (§5.6).

IMPORTANT: the test CSV below is controlled synthetic input. Official TARIC source sync is\nvalidated separately; this suite must not be described publicly as a normative TARIC oracle.\nAdapter: raw snapshot retention + parser version + normalized measure IDs.
Queries carry CN/origin/destination/as-of. Quota balance never asserted
unless the snapshot contains current balance state. Historical queries use
historical snapshots; parser schema changes fail closed.
"""
from __future__ import annotations

import unittest.mock as m
from pathlib import Path

from fastapi.testclient import TestClient

from app import eu_public_data as pub
from app.benchmark_harness import BenchmarkCase
from app.main import app
from app.taric_engine import resolve_taric
from tests.benchmarks.helpers import check

AS_OF = "2026-09-29"
CN = "72083900"

TARIC_CSV = ("cn_code,origin_country,measure_type,duty_rate,valid_from\n"
             "72083900,IN,THIRD_COUNTRY_DUTY,5%,2026-01-01\n"
             "72083900,IN,ANTIDUMPING,10%,2026-01-01\n")


def _seed(tmp) -> dict:
    with m.patch.object(pub, "CACHE", Path(tmp)):
        snap = pub.store_snapshot("taric", pub.parse_csv(TARIC_CSV, "taric", AS_OF),
                                  TARIC_CSV.encode())
        r = resolve_taric(CN, "IN", AS_OF, 100000, 100)
        return {"snap": snap, "resolve": r}


def test_taric_measures_resolve_exactly(tmp_path, monkeypatch):
    case = BenchmarkCase(suite_id="TARIC-LIVE", case_id="measures_001",
                         evidence_class="SYNTHETIC", as_of=AS_OF)
    monkeypatch.setattr(pub, "CACHE", tmp_path)
    pub.store_snapshot("taric", pub.parse_csv(TARIC_CSV, "taric", AS_OF),
                       TARIC_CSV.encode())
    r = resolve_taric(CN, "IN", AS_OF, 100000, 100)
    case.assert_and_emit(
        {"resolved": r["resolved"], "status": r["status"],
         "base": r["base_customs_duty_eur"], "defence": r["trade_defence_duty_eur"],
         "total": r["total_taric_duty_eur"],
         "snapshot_as_of": r["source"]["as_of"]},
        {"resolved": True, "status": "RESOLVED",
         "base": 5000, "defence": 10000, "total": 15000,
         "snapshot_as_of": AS_OF})


def test_taric_historical_snapshot(tmp_path, monkeypatch):
    """Historical query uses the historical snapshot, not today's (§5.6)."""
    case = BenchmarkCase(suite_id="TARIC-LIVE", case_id="historical_001",
                         evidence_class="SYNTHETIC", as_of="2026-09-20")
    monkeypatch.setattr(pub, "CACHE", tmp_path)
    pub.store_snapshot("taric", pub.parse_csv(TARIC_CSV, "taric", "2026-09-20"),
                       TARIC_CSV.encode())
    fresh = resolve_taric(CN, "IN", "2026-09-20", 100000, 100)
    stale = resolve_taric(CN, "IN", "2026-09-29", 100000, 100)
    case.assert_and_emit(
        {"fresh_resolved": fresh["resolved"],
         "stale_status": stale["status"], "stale_resolved": stale["resolved"]},
        {"fresh_resolved": True,
         "stale_status": "TARIC_SNAPSHOT_REQUIRED", "stale_resolved": False})


def test_taric_quota_balance_not_asserted_without_state(tmp_path, monkeypatch):
    """Quota measure without balance state → BLOCKED with QUOTA_BALANCE (§5.6)."""
    case = BenchmarkCase(suite_id="TARIC-LIVE", case_id="quota_unknown_001",
                         evidence_class="SYNTHETIC", as_of=AS_OF)
    monkeypatch.setattr(pub, "CACHE", tmp_path)
    csv = ("cn_code,origin_country,measure_type,duty_rate,quota_order_number,valid_from\n"
           "72083900,IN,TARIFF_QUOTA,0%,09.9803,2026-01-01\n")
    pub.store_snapshot("taric", pub.parse_csv(csv, "taric", AS_OF), csv.encode())
    r = resolve_taric(CN, "IN", AS_OF, 100000, 100)
    codes = [b.get("code") for b in r.get("blockers", [])]
    case.assert_and_emit(
        {"resolved": r["resolved"], "has_quota_blocker": "TARIC_QUOTA_BALANCE" in codes},
        {"resolved": False, "has_quota_blocker": True})


def test_taric_via_check_path(tmp_path, monkeypatch):
    """Production path: taric_payload through /v1/market-access/check."""
    case = BenchmarkCase(suite_id="TARIC-LIVE", case_id="check_path_001",
                         evidence_class="SYNTHETIC", as_of=AS_OF)
    monkeypatch.setattr(pub, "CACHE", tmp_path)
    pub.store_snapshot("taric", pub.parse_csv(TARIC_CSV, "taric", AS_OF),
                       TARIC_CSV.encode())
    client = TestClient(app)
    txn = {"transaction_ref": "TXN-TARIC-001", "order_id": "PO-EU-000342",
           "shipment_id": "SHP-T1", "line_id": "L1", "origin_country": "IN",
           "destination_country": "NL", "shipment_date": AS_OF,
           "line_value": 100000.0, "quantity": 100.0, "unit": "t",
           "cn_code": CN}
    decision = check(client, txn, as_of=AS_OF,
                     taric_payload={"cn_code": CN, "origin_country": "IN",
                                    "import_date": AS_OF,
                                    "customs_value_eur": 100000, "quantity_t": 100})
    by_id = {o["obligation_id"]: o for o in decision["obligation_results"]}
    case.assert_and_emit(
        {"status": decision["status"],
         "TARIC_DUTY": by_id.get("TARIC_DUTY", {}).get("status")},
        {"status": "READY", "TARIC_DUTY": "PASS"},
        decision_id=decision["decision_id"])
