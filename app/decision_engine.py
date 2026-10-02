"""Decision + policy engine (§6): deterministic aggregation, remediation contract.

DecisionPolicy is versioned; changing policy never rewrites historical decisions
(decisions pin policy_version + source/evidence snapshot hashes).
"""
from __future__ import annotations
from datetime import date, datetime, timezone
from uuid import uuid4
import json
from .db import connect, rows, row, audit
from .canonical_models import SCHEMA_VERSION, canonical_hash, decision_hash

POLICY_VERSION = "DECISION_POLICY_V1"

# §6.1 aggregation - versioned, explicit, fail-closed.
def aggregate(obligations: list[dict], policy_version: str = POLICY_VERSION) -> dict:
    if policy_version != POLICY_VERSION:
        raise ValueError(f"Unknown decision policy: {policy_version}")
    req = [o for o in obligations if o.get("required_for_release", True)]
    if any(o.get("status") == "ERROR" and o.get("required_for_release", True) for o in obligations):
        status, why = "ERROR", ["blocking obligation in ERROR"]
    elif any(o.get("status") == "FAIL" and o.get("severity") == "BLOCKING" for o in req):
        status, why = "BLOCKED", [f"{o.get('obligation_id')}: FAIL (blocking)" for o in req if o.get("status") == "FAIL" and o.get("severity") == "BLOCKING"]
    elif any(o.get("status") in ("MISSING", "STALE", "UNVERIFIED", "CONFLICTING", "EXPIRED", "SUPERSEDED")
             and o.get("severity") == "BLOCKING" for o in req):
        status = "BLOCKED"
        why = [f"{o.get('obligation_id')}: {o.get('status')}" for o in req
               if o.get("status") in ("MISSING", "STALE", "UNVERIFIED", "CONFLICTING", "EXPIRED", "SUPERSEDED")
               and o.get("severity") == "BLOCKING"]
    elif any(o.get("status") in ("MISSING", "STALE", "UNVERIFIED", "CONFLICTING", "EXPIRED", "SUPERSEDED")
             and o.get("severity") == "CONDITIONAL" for o in obligations):
        status = "CONDITIONAL"
        why = [f"{o.get('obligation_id')}: {o.get('status')} (conditional)" for o in obligations
               if o.get("status") in ("MISSING", "STALE", "UNVERIFIED", "CONFLICTING", "EXPIRED", "SUPERSEDED")]
    elif all(o.get("status") in ("PASS", "NOT_APPLICABLE") or not o.get("required_for_release", True) for o in obligations):
        status, why = ("READY", []) if obligations else ("CONDITIONAL", ["no obligations evaluated"])
    else:
        status = "CONDITIONAL"
        why = [f"{o.get('obligation_id')}: {o.get('status')}" for o in obligations if o.get("status") not in ("PASS", "NOT_APPLICABLE")]
    return {"status": status, "blocking_reasons": why, "policy_version": policy_version}


def build_decision(transaction_ref: str, obligations: list[dict], *, as_of: str | None = None,
                   source_snapshot_refs: list[dict] | None = None,
                   evidence_snapshot_refs: list[str] | None = None,
                   predecessor_id: str | None = None,
                   policy_version: str = POLICY_VERSION) -> dict:
    agg = aggregate(obligations, policy_version)
    d = {"decision_id": str(uuid4()), "schema_version": SCHEMA_VERSION,
         "transaction_ref": transaction_ref,
         "as_of": as_of or date.today().isoformat(),
         "status": agg["status"], "obligation_results": obligations,
         "blocking_reasons": agg["blocking_reasons"],
         "source_snapshot_refs": source_snapshot_refs or [],
         "evidence_snapshot_refs": evidence_snapshot_refs or [],
         "predecessor_id": predecessor_id, "policy_version": policy_version,
         "generated_at": datetime.now(timezone.utc).isoformat()}
    d["decision_hash"] = decision_hash(d)
    return d


def persist_decision(decision: dict) -> dict:
    with connect() as conn:
        conn.execute(
            "INSERT INTO canonical_decisions(decision_id,transaction_ref,as_of,status,policy_version,"
            "predecessor_id,decision_hash,payload_json,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (decision["decision_id"], decision["transaction_ref"], decision["as_of"],
             decision["status"], decision["policy_version"], decision.get("predecessor_id"),
             decision["decision_hash"], json.dumps(decision), decision["generated_at"]))
        audit(conn, decision["transaction_ref"], "decision.persisted",
              {"decision_id": decision["decision_id"], "status": decision["status"],
               "policy": decision["policy_version"], "hash": decision["decision_hash"]})
    return decision


def get_decision(decision_id: str) -> dict | None:
    with connect() as conn:
        r = row(conn, "SELECT payload_json FROM canonical_decisions WHERE decision_id=?", (decision_id,))
        return json.loads(r["payload_json"]) if r else None


def replay_decision(decision_id: str) -> dict:
    """Historical replay: re-aggregate the pinned obligation snapshot (§12 P0-C).

    Uses the stored obligation/source/evidence refs - never mutable current state.
    Byte-for-byte decision-equivalent except run metadata (new decision_id /
    generated_at); predecessor links the replay chain.
    """
    orig = get_decision(decision_id)
    if not orig:
        raise ValueError("decision not found")
    agg = aggregate(orig["obligation_results"], orig.get("policy_version", POLICY_VERSION))
    rep = {**orig, "decision_id": str(uuid4()),
           "generated_at": datetime.now(timezone.utc).isoformat(),
           "predecessor_id": decision_id, "replay_of": decision_id,
           "replay_status": agg["status"]}
    rep["decision_hash"] = decision_hash({k: v for k, v in rep.items() if k != "replay_status"})
    assert rep["replay_status"] == orig["status"], "replay diverged from pinned decision"
    return persist_decision({k: v for k, v in rep.items() if k != "replay_status"})


# §6.2 remediation contract
def build_remediation_action(issue_ref: str, requested: str, owner_role: str,
                             affected_transactions: list[dict],
                             priority: int = 0, prerequisites: list[str] | None = None,
                             source_refs: list[str] | None = None,
                             evidence_refs: list[str] | None = None,
                             objective: str = "unlock_value") -> dict:
    """unlock_value = unique tx value releasable if this is the last blocker,
    else marginal unlock value. Never presented without the configured objective."""
    unique = sum(t.get("line_value", t.get("value_eur", 0)) for t in affected_transactions)
    return {"action_id": str(uuid4()), "schema_version": SCHEMA_VERSION,
            "issue_ref": issue_ref, "requested_evidence_action": requested,
            "owner_role": owner_role, "priority": priority,
            "affected_transactions": [t.get("id", t.get("shipment_id", "")) for t in affected_transactions],
            "unlock_value": round(unique, 2), "marginal_unlock_value": round(unique, 2),
            "prerequisites": prerequisites or [], "objective": objective,
            "source_refs": source_refs or [], "evidence_refs": evidence_refs or []}
