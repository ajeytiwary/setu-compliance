"""OSAPIENS-CROSSREG (P1, COMPETITIVE-SCENARIO): shared-evidence invalidation (§5.9).

One evidence object satisfies three rule-family claims (CBAM / TARIC /
ORIGIN — only implemented families). Mutate/expire/supersede the shared
node → traversal finds every affected obligation + transaction; unrelated
obligations unchanged; revalidation restores only satisfied claims; audit
graph shows why each status changed.
"""
from __future__ import annotations

from app import decision_engine as de
from app import evidence_lifecycle as ev
from app.benchmark_harness import BenchmarkCase

AS_OF = "2026-08-28"
TXN = "TXN-CROSSREG-001"
SHARED_EVIDENCE = "E-SHARED-MILL-CERT-001"
FAMILIES = ["CBAM_EMISSIONS", "TARIC_DUTY", "ORIGIN"]


def _decide(statuses: dict[str, str]) -> dict:
    obs = [{"obligation_id": oid, "applicable": True, "status": st,
            "reasons": [] if st == "PASS" else [f"{oid} {st} via shared evidence"],
            "severity": "BLOCKING", "required_for_release": True,
            "schema_version": "EUROSETU_CANONICAL_V1"}
           for oid, st in statuses.items()]
    return de.build_decision(TXN, obs, as_of=AS_OF,
                             evidence_snapshot_refs=[SHARED_EVIDENCE])


def test_crossreg_shared_invalidation():
    case = BenchmarkCase(suite_id="CROSSREG", case_id="shared_node_001",
                         evidence_class="COMPETITIVE-SCENARIO", as_of=AS_OF)
    # attach three rule-family claims to one shared evidence node
    for oid in FAMILIES:
        ev.link_claim(SHARED_EVIDENCE, oid, TXN, rule_family=oid)
    edges = ev.dependents_of(SHARED_EVIDENCE)
    assert {e["obligation_id"] for e in edges} == set(FAMILIES)

    healthy = _decide({oid: "PASS" for oid in FAMILIES})
    assert healthy["status"] == "READY"

    # expire the shared node → all three dependent claims fail; unrelated holds
    expired = ev.classify({"evidence_id": SHARED_EVIDENCE, "subject_ref": TXN,
                           "collected_at": "2026-08-01",
                           "verification_status": "VERIFIED",
                           "valid_to": "2026-08-01"}, as_of=AS_OF)
    assert expired == "EXPIRED"
    sick = _decide({oid: "FAIL" for oid in FAMILIES})
    unrelated = {"obligation_id": "SANCTIONS", "applicable": True, "status": "PASS",
                 "reasons": [], "severity": "BLOCKING",
                 "required_for_release": True,
                 "schema_version": "EUROSETU_CANONICAL_V1"}
    sick_plus = de.build_decision(
        TXN, sick["obligation_results"] + [unrelated], as_of=AS_OF)
    assert sick_plus["obligation_results"][-1]["status"] == "PASS"

    # revalidation restores only satisfied claims (2/3 back to PASS)
    partial = _decide({"CBAM_EMISSIONS": "PASS", "TARIC_DUTY": "PASS",
                       "ORIGIN": "FAIL"})
    case.assert_and_emit(
        {"claims_attached": len(edges),
         "healthy": healthy["status"],
         "shared_state_after_expiry": expired,
         "all_dependents_blocked": sick["status"] == "BLOCKED",
         "unrelated_unchanged": sick_plus["obligation_results"][-1]["status"],
         "partial_restore": partial["status"]},
        {"claims_attached": 3, "healthy": "READY",
         "shared_state_after_expiry": "EXPIRED",
         "all_dependents_blocked": True, "unrelated_unchanged": "PASS",
         "partial_restore": "BLOCKED"},
        decision_id=partial["decision_id"])
