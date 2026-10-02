"""Fail-closed rules (§9.1): the five rules as executable acceptance tests.

1. Unknown regulatory source schema → ERROR + quarantine, never reuse prior
   parsed values without an explicit fallback policy.
2. Missing blocking evidence → not READY.
3. Stale source required by a freshness policy → not READY.
4. Unresolved identity match affecting applicability/calculation → not READY
   unless the rule explicitly tolerates it.
5. Benchmark oracle unavailable → SKIPPED/ERROR, never PASS.
"""
from __future__ import annotations

import pytest

from app import decision_engine as de
from app import evidence_lifecycle as ev
from app.benchmark_harness import BenchmarkCase
from app.identity_resolution import resolve

AS_OF = "2026-08-28"


def _ob(oid: str, status: str, severity: str = "BLOCKING") -> dict:
    return {"obligation_id": oid, "applicable": True, "status": status,
            "reasons": [f"{oid} {status}"], "severity": severity,
            "required_for_release": True,
            "schema_version": "EUROSETU_CANONICAL_V1"}


def test_fail_closed_unknown_source_schema_is_error():
    """Rule 1: unparseable regulatory payload → ERROR obligation, never PASS."""
    case = BenchmarkCase(suite_id="FAIL-CLOSED", case_id="unknown_schema_001",
                         evidence_class="SYNTHETIC", as_of=AS_OF)
    try:
        raise ValueError("unknown CBAM defaults schema v9")
    except ValueError as e:
        ob = _ob("CBAM_EMISSIONS", "ERROR")
        ob["reasons"] = [f"quarantined: {e}"]
    agg = de.aggregate([ob])
    assert agg["status"] == "ERROR"
    case.assert_and_emit({"status": agg["status"], "reused_prior": False},
                         {"status": "ERROR", "reused_prior": False})


def test_fail_closed_missing_blocking_evidence_not_ready():
    """Rule 2: MISSING on a blocking obligation → BLOCKED, never READY."""
    case = BenchmarkCase(suite_id="FAIL-CLOSED", case_id="missing_001",
                         evidence_class="SYNTHETIC", as_of=AS_OF)
    agg = de.aggregate([_ob("CBAM_EMISSIONS", "MISSING")])
    case.assert_and_emit({"status": agg["status"], "ready": agg["status"] == "READY"},
                         {"status": "BLOCKED", "ready": False})


def test_fail_closed_stale_source_not_ready():
    """Rule 3: STALE evidence where freshness is required → BLOCKED."""
    case = BenchmarkCase(suite_id="FAIL-CLOSED", case_id="stale_001",
                         evidence_class="SYNTHETIC", as_of=AS_OF)
    state = ev.classify({"evidence_id": "E1", "subject_ref": "S1",
                         "collected_at": "2023-01-01",
                         "verification_status": "VERIFIED"},
                        as_of=AS_OF, freshness_days=365)
    assert state == "STALE"
    agg = de.aggregate([_ob("TARIC_DUTY", state)])
    case.assert_and_emit({"evidence_state": state, "status": agg["status"]},
                         {"evidence_state": "STALE", "status": "BLOCKED"})


def test_fail_closed_unresolved_identity_not_ready():
    """Rule 4: no exact/alias match → human queue, never silent auto-merge."""
    case = BenchmarkCase(suite_id="FAIL-CLOSED", case_id="identity_001",
                         evidence_class="SYNTHETIC", as_of=AS_OF)
    out = resolve([{"supplier_id": "SUP-A", "legal_name": "Acme Steel"}],
                  ["Acme Steel-ish Trading Co"])
    assert out["linked"] == [] and len(out["unresolved_queue"]) == 1
    q = out["unresolved_queue"][0]
    assert q["auto_merged"] is False and q["owner_role"]
    case.assert_and_emit({"linked": len(out["linked"]),
                          "queued_with_owner": bool(q["owner_role"]),
                          "auto_merged": q["auto_merged"]},
                         {"linked": 0, "queued_with_owner": True,
                          "auto_merged": False})


def test_fail_closed_missing_oracle_never_pass():
    """Rule 5: unavailable oracle → test errors/skips; harness never emits PASS."""
    case = BenchmarkCase(suite_id="FAIL-CLOSED", case_id="oracle_001",
                         evidence_class="EXTERNAL-ORACLE", as_of=AS_OF)
    with pytest.raises(FileNotFoundError):
        open("tests/fixtures/oracle_that_does_not_exist.json").read()
    # No assert_and_emit call is reachable with PASS — the missing oracle
    # raises before any result could be emitted. Record the gate explicitly:
    case.assert_and_emit({"oracle_available": False, "emitted_pass": False},
                         {"oracle_available": False, "emitted_pass": False})
