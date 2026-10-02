"""Evidence lifecycle (§3.3, §5.11): VALID/STALE/EXPIRED/SUPERSEDED/CONFLICTING/UNVERIFIED/MISSING.

Deterministic clock: callers pass as_of explicitly; CI never depends on wall-clock.
Freshness policy (STALE threshold) is separate from legal validity (valid_to).
"""
from __future__ import annotations
from datetime import date, datetime, timezone
from uuid import uuid4
import json
from .db import connect, rows, row, audit
from .canonical_models import SCHEMA_VERSION, canonical_hash

STATES = ("VALID", "STALE", "EXPIRED", "SUPERSEDED", "CONFLICTING", "UNVERIFIED", "MISSING")


def classify(ev: dict, *, as_of: str | None = None, freshness_days: int = 365,
             required_verification: str = "VERIFIED") -> str:
    """Classify one evidence object at an as-of date. Pure function (no DB)."""
    today = date.fromisoformat(as_of) if as_of else date.today()
    if ev.get("superseded_by"):
        return "SUPERSEDED"
    if ev.get("conflicting"):
        return "CONFLICTING"
    vt = ev.get("valid_to")
    if vt and today > date.fromisoformat(str(vt)[:10]):
        return "EXPIRED"
    vf = ev.get("valid_from")
    if vf and today < date.fromisoformat(str(vf)[:10]):
        return "UNVERIFIED"  # not yet effective - cannot be relied upon
    status = str(ev.get("status", ev.get("verification_status", "UNVERIFIED"))).upper()
    if status not in ("VERIFIED", "VALID", "APPROVED", "ACCEPTED"):
        # verification below obligation policy
        collected = str(ev.get("collected_at", ev.get("created_at", today.isoformat())))[:10]
        try:
            age = (today - date.fromisoformat(collected)).days
        except ValueError:
            age = 0
        if vt and today > date.fromisoformat(str(vt)[:10]):
            return "EXPIRED"
        return "UNVERIFIED"
    collected = str(ev.get("collected_at", ev.get("created_at", today.isoformat())))[:10]
    try:
        age = (today - date.fromisoformat(collected)).days
    except ValueError:
        age = 0
    if age > freshness_days:
        return "STALE"
    return "VALID"


def evaluate_requirement(evidence: list[dict], *, as_of: str | None = None,
                         freshness_days: int = 365) -> dict:
    """Evaluate one requirement's evidence set → state + blocking signal."""
    if not evidence:
        return {"state": "MISSING", "usable": [], "detail": "no evidence objects"}
    states = [(e, classify(e, as_of=as_of, freshness_days=freshness_days)) for e in evidence]
    # conflict: two active objects assert incompatible content hashes for same type
    actives = [(e, s) for e, s in states if s in ("VALID", "STALE")]
    hashes = {e.get("sha256", e.get("content_hash")) for e, _ in actives}
    if len(actives) >= 2 and len(hashes) > 1 and all(
            e.get("subject_ref") == actives[0][0].get("subject_ref") for e, _ in actives):
        return {"state": "CONFLICTING", "usable": [],
                "detail": f"{len(actives)} active objects disagree", "objects": [e.get("id", e.get("evidence_id")) for e, _ in actives]}
    if any(s == "SUPERSEDED" for _, s in states) and not actives:
        return {"state": "SUPERSEDED", "usable": [], "detail": "superseded, no active replacement"}
    if any(s == "VALID" for _, s in states):
        return {"state": "VALID", "usable": [e.get("id", e.get("evidence_id")) for e, s in states if s == "VALID"]}
    for s in ("STALE", "EXPIRED", "UNVERIFIED"):
        if any(x == s for _, x in states):
            return {"state": s, "usable": [],
                    "detail": f"best available state is {s}"}
    return {"state": "MISSING", "usable": [], "detail": "no usable evidence"}


def put_object(*, type: str, subject_ref: str, content: bytes | str,
               issuer: str = "", source_uri_ref: str = "",
               valid_from: str | None = None, valid_to: str | None = None,
               verification_status: str = "UNVERIFIED",
               supersedes: str | None = None, confidentiality: str = "internal",
               tenant_id: str = "default") -> dict:
    """Store an evidence object (metadata + hash; raw bytes stay in evidence_store)."""
    from . import evidence_store as store
    raw = content.encode() if isinstance(content, str) else content
    blob = store.put(tenant_id, subject_ref, f"{type}.bin", raw,
                     {"evidence_type": type, "issuer": issuer})
    eid, now = str(uuid4()), datetime.now(timezone.utc).isoformat()
    rec = {"evidence_id": eid, "schema_version": SCHEMA_VERSION, "type": type,
           "subject_ref": subject_ref, "issuer": issuer, "source_uri_ref": source_uri_ref,
           "content_hash": blob["sha256"], "collected_at": now,
           "valid_from": valid_from, "valid_to": valid_to,
           "verification_status": verification_status, "supersedes": supersedes,
           "confidentiality": confidentiality, "tenant_id": tenant_id}
    with connect() as conn:
        if supersedes:
            conn.execute("UPDATE evidence_objects SET superseded_by=? WHERE evidence_id=?",
                         (eid, supersedes))
        conn.execute(
            "INSERT INTO evidence_objects(evidence_id,tenant_id,type,subject_ref,issuer,"
            "source_uri_ref,content_hash,collected_at,valid_from,valid_to,"
            "verification_status,supersedes,superseded_by,confidentiality,payload_json,created_at)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (eid, tenant_id, type, subject_ref, issuer, source_uri_ref, blob["sha256"],
             now, valid_from, valid_to, verification_status, supersedes, None,
             confidentiality, json.dumps(rec), now))
        audit(conn, subject_ref, "evidence.stored", {"evidence_id": eid, "type": type})
    return rec


def mark_conflicting(evidence_id: str) -> None:
    with connect() as conn:
        conn.execute("UPDATE evidence_objects SET conflicting=1 WHERE evidence_id=?", (evidence_id,))


def dependents_of(evidence_id: str) -> list[dict]:
    """Obligation/transaction edges that reference this evidence node (§5.9)."""
    with connect() as conn:
        try:
            return rows(conn, "SELECT * FROM evidence_claim_edges WHERE evidence_id=?", (evidence_id,))
        except Exception:
            return []


def link_claim(evidence_id: str, obligation_id: str, transaction_ref: str, rule_family: str) -> None:
    with connect() as conn:
        conn.execute("INSERT OR IGNORE INTO evidence_claim_edges(evidence_id,obligation_id,transaction_ref,rule_family,created_at)"
                     " VALUES(?,?,?,?,?)",
                     (evidence_id, obligation_id, transaction_ref, rule_family,
                      datetime.now(timezone.utc).isoformat()))
