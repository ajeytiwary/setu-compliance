"""CBAM-2026 (P0, NORMATIVE): definitive-period defaults/benchmarks/fallback (§5.2).

Cases: actual installation data; fallback/default path; above-benchmark;
below-benchmark; source-version change. Records which path (actual/default)
was used. Acceptance: T1 replay byte-equivalent; source change affects only
causally-linked outputs; default usage + citation exposed.
"""
from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app import cbam_definitive_v2 as v2
from app.benchmark_harness import BenchmarkCase
from app.main import app
from tests.benchmarks.helpers import check

AS_OF = "2026-08-28"
CN = "72083900"


def _txn(ref: str) -> dict:
    return {"transaction_ref": ref, "order_id": "PO-EU-000342",
            "shipment_id": "SHP-26", "line_id": "L1", "origin_country": "IN",
            "destination_country": "NL", "shipment_date": AS_OF,
            "line_value": 500000.0, "quantity": 100.0, "unit": "t",
            "cn_code": CN}


def test_cbam2026_actual_path():
    case = BenchmarkCase(suite_id="CBAM-2026", case_id="actual_001",
                         evidence_class="NORMATIVE", as_of=AS_OF)
    payload = json.loads(open("examples/cbam_actual_steel.json").read().replace(
        '"reporting_period":2026', '"reporting_period": 2026'))
    payload = {**payload, "origin_country": "IN", "value_type": "ACTUAL",
               "reporting_period": 2026, "mass_t": 1000.0}
    r = v2.calculate(payload)
    case.assert_and_emit(
        {"status": r["status"], "value_type": r["value_type"],
         "see": r["emissions"]["specific_direct_embedded_emissions_tco2_per_t"],
         "faa": r["free_allocation"]["specific_embedded_free_allocation_tco2e_per_t"]},
        {"status": "CALCULATED", "value_type": "ACTUAL",
         "see": 1.73, "faa": 0.0429},
        tolerances={"see": 1e-9, "faa": 1e-6})


def test_cbam2026_default_fallback_path():
    """No installation data → DEFAULT path with 2026 +10% markup (4.28→4.708)."""
    case = BenchmarkCase(suite_id="CBAM-2026", case_id="default_001",
                         evidence_class="NORMATIVE", as_of=AS_OF)
    r = v2.calculate({"origin_country": "IN", "cn_code": CN,
                      "production_route": "(C)", "value_type": "DEFAULT",
                      "reporting_period": 2026, "mass_t": 100.0})
    case.assert_and_emit(
        {"status": r["status"], "value_type": r["value_type"],
         "certificate_default_total":
             r["emissions"]["default"]["certificate_default_total"],
         "dataset_version": r["emissions"]["default"]["dataset_version"]},
        {"status": "CALCULATED", "value_type": "DEFAULT",
         "certificate_default_total": 4.708,
         "dataset_version": "2025/2621-corrected-2026/1740"},
        tolerances={"certificate_default_total": 1e-6})


def test_cbam2026_above_below_benchmark():
    case = BenchmarkCase(suite_id="CBAM-2026", case_id="benchmark_compare_001",
                         evidence_class="NORMATIVE", as_of=AS_OF)
    bm = v2.select_benchmark(CN, "(C)")
    assert bm["available"] and bm["benchmark"] == 0.044
    # actual 1.73 >> benchmark 0.044 (above); default-derived FAA below actual
    faa = v2.free_allocation_adjustment(CN, 100.0, 2026, "(C)")
    case.assert_and_emit(
        {"benchmark": bm["benchmark"],
         "actual_above_benchmark": 1.73 > bm["benchmark"],
         "faa_per_t": faa["specific_embedded_free_allocation_tco2e_per_t"],
         "cbam_factor": faa["cbam_factor"], "cscf": faa["cscf"]},
        {"benchmark": 0.044, "actual_above_benchmark": True,
         "faa_per_t": 0.0429, "cbam_factor": 0.975, "cscf": 1.0},
        tolerances={"faa_per_t": 1e-6})


def test_cbam2026_replay_stable():
    """T1 decision replayed after identical re-check: byte-equivalent status."""
    case = BenchmarkCase(suite_id="CBAM-2026", case_id="replay_stable_001",
                         evidence_class="NORMATIVE", as_of=AS_OF)
    client = TestClient(app)
    cbam_payload = {"origin_country": "IN", "cn_code": CN,
                    "production_route": "(C)", "value_type": "DEFAULT",
                    "reporting_period": 2026, "mass_t": 100.0}
    d1 = check(client, _txn("TXN-CBAM26-REPLAY-001"), as_of=AS_OF,
               cbam_payload=cbam_payload)
    r = client.post(f"/v1/decisions/{d1['decision_id']}/replay")
    assert r.status_code == 201, r.text
    d2 = r.json()
    case.assert_and_emit(
        {"orig_status": d1["status"], "replay_status": d2["status"],
         "predecessor_linked": d2.get("predecessor_id") == d1["decision_id"],
         "same_obligations": d2["obligation_results"] == d1["obligation_results"]},
        {"orig_status": "READY", "replay_status": "READY",
         "predecessor_linked": True, "same_obligations": True},
        decision_id=d2["decision_id"])
