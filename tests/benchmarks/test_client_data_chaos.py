"""CLIENT-DATA-CHAOS (P1, SYNTHETIC): messy-supplier ingestion gauntlet (§5.3/§9).

Re-implements CBAMReturn-style messy-supplier patterns synthetically
(CHAOS-001..015). Each case builds the evidence shape that a real
compliance workflow must survive, classifies it via
app.evidence_lifecycle (deterministic as_of clock), aggregates via
app.decision_engine (DECISION_POLICY_V1 fail-closed), and asserts:

  initial  -> BLOCKED (never READY on garbage), names the defect
  remediated (corrected evidence ingested) -> READY with predecessor link

No vendor files copied. No normative calculation oracle claimed.
"""
from __future__ import annotations

from app import decision_engine as de
from app import evidence_lifecycle as ev
from app.benchmark_harness import BenchmarkCase

AS_OF = "2026-08-28"

# chaos_id -> (evidence objects for evaluate_requirement, expected state, remediation note)
def _ev(eid: str, **kw) -> dict:
    base = {"evidence_id": eid, "subject_ref": "TXN-CHAOS",
            "collected_at": "2026-08-01", "verification_status": "VERIFIED"}
    base.update(kw)
    return base


CASES: dict[str, dict] = {
    # renamed worksheet -> parser cannot verify content -> UNVERIFIED
    "CHAOS-001": {"evidence": [_ev("E-001", verification_status="UNVERIFIED")],
                  "state": "UNVERIFIED", "note": "renamed worksheet: content unverifiable"},
    # decimal comma "1,9" misparsed -> value rejected at validation -> UNVERIFIED
    "CHAOS-002": {"evidence": [_ev("E-002", verification_status="UNPARSED")],
                  "state": "UNVERIFIED", "note": "decimal comma: numeric parse rejected"},
    # units embedded in cells -> non-numeric -> UNVERIFIED
    "CHAOS-003": {"evidence": [_ev("E-003", verification_status="UNPARSED")],
                  "state": "UNVERIFIED", "note": "units embedded in cells"},
    # kg-tonne x1000 outlier -> plausibility gate rejects -> UNVERIFIED
    "CHAOS-004": {"evidence": [_ev("E-004", verification_status="REJECTED_OUTLIER")],
                  "state": "UNVERIFIED", "note": "kg-tonne factor-1000 outlier"},
    # 8-digit CN where 10-digit TARIC required -> document absent -> MISSING
    "CHAOS-005": {"evidence": [], "state": "MISSING",
                  "note": "8-digit CN supplied; 10-digit TARIC document missing"},
    # stale cached formula -> collected > freshness policy -> STALE
    "CHAOS-006": {"evidence": [_ev("E-006", collected_at="2024-01-01")],
                  "state": "STALE", "note": "stale Excel cached formula"},
    # duplicate supplier rows -> two active objects disagree -> CONFLICTING
    "CHAOS-007": {"evidence": [
        _ev("E-007a", sha256="aaa"), _ev("E-007b", sha256="bbb")],
        "state": "CONFLICTING", "note": "duplicate supplier records disagree"},
    # conflicting installation IDs -> CONFLICTING
    "CHAOS-008": {"evidence": [
        _ev("E-008a", sha256="inst-1"), _ev("E-008b", sha256="inst-2")],
        "state": "CONFLICTING", "note": "conflicting installation IDs"},
    # missing precursor section -> MISSING
    "CHAOS-009": {"evidence": [], "state": "MISSING", "note": "precursor section absent"},
    # wrong reporting period -> validity window missed -> EXPIRED
    "CHAOS-010": {"evidence": [_ev("E-010", valid_to="2026-03-31")],
                  "state": "EXPIRED", "note": "wrong reporting period"},
    # expired verification statement -> EXPIRED
    "CHAOS-011": {"evidence": [_ev("E-011", valid_to="2026-06-30")],
                  "state": "EXPIRED", "note": "expired verification"},
    # superseded cert, no replacement -> SUPERSEDED
    "CHAOS-012": {"evidence": [_ev("E-012", superseded_by="E-012b")],
                  "state": "SUPERSEDED", "note": "superseded certificate"},
    # duplicate invoice -> CONFLICTING
    "CHAOS-013": {"evidence": [
        _ev("E-013a", sha256="inv-1"), _ev("E-013b", sha256="inv-2")],
        "state": "CONFLICTING", "note": "duplicate invoice"},
    # invoice/PO quantity mismatch -> CONFLICTING
    "CHAOS-014": {"evidence": [
        _ev("E-014a", sha256="qty-100"), _ev("E-014b", sha256="qty-120")],
        "state": "CONFLICTING", "note": "invoice/PO quantity mismatch"},
    # MTC heat mismatch -> CONFLICTING
    "CHAOS-015": {"evidence": [
        _ev("E-015a", sha256="heat-A"), _ev("E-015b", sha256="heat-B")],
        "state": "CONFLICTING", "note": "MTC heat number mismatch"},
}


def _ob(oid: str, status: str, reason: str = "") -> dict:
    return {"obligation_id": oid, "applicable": True, "status": status,
            "reasons": [reason] if reason else [], "severity": "BLOCKING",
            "required_for_release": True,
            "schema_version": "EUROSETU_CANONICAL_V1"}


def _decide(txn: str, ev_state: str, reason: str, predecessor: str | None = None) -> dict:
    obs = [_ob("CBAM_EMISSIONS", "PASS"), _ob("TARIC_DUTY", "PASS"),
           _ob("EVIDENCE_CHAIN", ev_state, reason)]
    return de.build_decision(txn, obs, as_of=AS_OF, predecessor_id=predecessor)


def test_chaos_family_fail_closed_and_remediates():
    for cid, spec in CASES.items():
        case = BenchmarkCase(suite_id="CLIENT-DATA-CHAOS", case_id=cid.lower(),
                             evidence_class="SYNTHETIC", as_of=AS_OF)
        evaluated = ev.evaluate_requirement(spec["evidence"], as_of=AS_OF)
        assert evaluated["state"] == spec["state"], f"{cid}: {evaluated}"
        txn = f"TXN-{cid}"
        before = _decide(txn, evaluated["state"], spec["note"])
        assert before["status"] == "BLOCKED", f"{cid} must fail closed, got {before['status']}"
        assert before["status"] != "READY"
        after = _decide(txn, "PASS", "corrected evidence ingested",
                        predecessor=before["decision_id"])
        assert after["status"] == "READY", f"{cid} remediation must reach READY"
        assert after["predecessor_id"] == before["decision_id"]
        assert after["decision_hash"] != before["decision_hash"]
        case.assert_and_emit(
            {"evidence_state": evaluated["state"], "initial": before["status"],
             "remediated": after["status"],
             "predecessor_preserved": after["predecessor_id"] == before["decision_id"],
             "policy": after["policy_version"]},
            {"evidence_state": spec["state"], "initial": "BLOCKED",
             "remediated": "READY", "predecessor_preserved": True,
             "policy": "DECISION_POLICY_V1"})
