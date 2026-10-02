"""v1 canonical APIs (§7): transactions, evidence, sources, market-access check.

Thin deterministic layer: callers evaluate domain engines (CBAM/TARIC/origin)
then POST obligation results; the server aggregates via the versioned
DecisionPolicy, pins source/evidence snapshot refs + as_of, and persists an
immutable decision. Replay uses only pinned refs — never mutable state.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .db import connect, rows, row, audit
from .canonical_models import SCHEMA_VERSION
from . import decision_engine as de
from . import evidence_lifecycle as ev
from . import source_registry as sr

router = APIRouter(prefix="/v1", tags=["canonical-v1"])

MIGRATION = """
CREATE TABLE IF NOT EXISTS canonical_transactions(
  transaction_ref TEXT PRIMARY KEY, order_id TEXT, shipment_id TEXT, line_id TEXT,
  payload_json TEXT NOT NULL, idempotency_key TEXT, created_at TEXT NOT NULL);
CREATE UNIQUE INDEX IF NOT EXISTS idx_ctx_idem ON canonical_transactions(idempotency_key);
"""


def _migrate():
    with connect() as conn:
        conn.executescript(MIGRATION)


_migrate()


class TransactionIn(BaseModel):
    transaction_ref: str | None = None
    order_id: str = ""
    shipment_id: str = ""
    line_id: str = ""
    seller: str = ""
    buyer: str = ""
    importer: str = ""
    origin_country: str = "IN"
    destination_country: str = "NL"
    shipment_date: str = "2026-08-28"
    line_value: float = 0.0
    quantity: float = 0.0
    unit: str = "t"
    cn_code: str = ""
    extra: dict = Field(default_factory=dict)


class EvidenceIn(BaseModel):
    type: str
    subject_ref: str
    content: str = ""
    issuer: str = ""
    source_uri_ref: str = ""
    valid_from: str | None = None
    valid_to: str | None = None
    verification_status: str = "UNVERIFIED"
    supersedes: str | None = None
    confidentiality: str = "internal"


class SourceSnapshotIn(BaseModel):
    source_id: str
    authority: str = ""
    title: str = ""
    legal_basis: list[str] = Field(default_factory=list)
    version: str
    effective_from: str | None = None
    effective_to: str | None = None
    content: str = ""
    parser_version: str = "v1"


class CheckIn(BaseModel):
    transaction_ref: str
    as_of: str
    obligations: list[dict] = Field(default_factory=list)
    source_snapshot_refs: list[dict] = Field(default_factory=list)
    evidence_snapshot_refs: list[str] = Field(default_factory=list)
    predecessor_id: str | None = None
    # optional auto-evaluated engine payloads (evaluated server-side, pinned)
    cbam_payload: dict | None = None
    taric_payload: dict | None = None


def _auto_obligations(cbam_payload: dict | None, taric_payload: dict | None,
                      as_of: str) -> list[dict]:
    out: list[dict] = []
    if cbam_payload is not None:
        try:
            from . import cbam_definitive_v2 as cbam2
            r = cbam2.calculate(cbam_payload)
            ok = r.get("status") == "CALCULATED"
            out.append({"obligation_id": "CBAM_EMISSIONS", "applicable": True,
                        "status": "PASS" if ok else "FAIL",
                        "reasons": [] if ok else [str(r.get("blockers", r.get("status")))],
                        "calculation_refs": [json.dumps(r, default=str)[:2000]],
                        "severity": "BLOCKING", "required_for_release": True,
                        "schema_version": SCHEMA_VERSION})
        except Exception as e:
            out.append({"obligation_id": "CBAM_EMISSIONS", "applicable": True,
                        "status": "ERROR", "reasons": [f"{type(e).__name__}: {e}"],
                        "severity": "BLOCKING", "required_for_release": True,
                        "schema_version": SCHEMA_VERSION})
    if taric_payload is not None:
        try:
            from .taric_engine import resolve_taric
            p = taric_payload
            r = resolve_taric(p["cn_code"], p.get("origin_country", "IN"),
                              p.get("import_date", as_of),
                              p.get("customs_value_eur", 0), p.get("quantity_t", 0),
                              p.get("documents"), p.get("additional_code"))
            ok = r.get("status") == "RESOLVED"
            out.append({"obligation_id": "TARIC_DUTY", "applicable": True,
                        "status": "PASS" if ok else "FAIL",
                        "reasons": [] if ok else [str(r.get("blockers", []))],
                        "calculation_refs": [json.dumps(
                            {k: r.get(k) for k in ("status", "total_taric_duty_eur",
                                                   "base_customs_duty_eur")}, default=str)],
                        "severity": "BLOCKING", "required_for_release": True,
                        "schema_version": SCHEMA_VERSION})
        except Exception as e:
            out.append({"obligation_id": "TARIC_DUTY", "applicable": True,
                        "status": "ERROR", "reasons": [f"{type(e).__name__}: {e}"],
                        "severity": "BLOCKING", "required_for_release": True,
                        "schema_version": SCHEMA_VERSION})
    return out


@router.post("/transactions", status_code=201)
def create_transaction(x: TransactionIn, request_idem: str | None = None):
    from fastapi import Request  # deferred
    _migrate()
    ref = x.transaction_ref or f"TXN-{uuid4().hex[:8].upper()}"
    payload = x.model_dump()
    payload["schema_version"] = SCHEMA_VERSION
    now = datetime.now(timezone.utc).isoformat()
    with connect() as conn:
        hit = row(conn, "SELECT payload_json FROM canonical_transactions WHERE transaction_ref=?", (ref,))
        if hit:
            return {**json.loads(hit["payload_json"]), "deduplicated": True}
        conn.execute("INSERT INTO canonical_transactions(transaction_ref,order_id,shipment_id,line_id,"
                     "payload_json,idempotency_key,created_at) VALUES(?,?,?,?,?,?,?)",
                     (ref, x.order_id, x.shipment_id, x.line_id,
                      json.dumps(payload), request_idem, now))
        audit(conn, ref, "transaction.created", {"transaction_ref": ref})
    return {**payload, "transaction_ref": ref, "deduplicated": False}


@router.post("/evidence", status_code=201)
def submit_evidence(x: EvidenceIn):
    rec = ev.put_object(type=x.type, subject_ref=x.subject_ref, content=x.content,
                        issuer=x.issuer, source_uri_ref=x.source_uri_ref,
                        valid_from=x.valid_from, valid_to=x.valid_to,
                        verification_status=x.verification_status,
                        supersedes=x.supersedes, confidentiality=x.confidentiality)
    return rec


@router.post("/sources/snapshots", status_code=201)
def register_snapshot(x: SourceSnapshotIn):
    return sr.register(source_id=x.source_id, authority=x.authority, title=x.title,
                       legal_basis=x.legal_basis, version=x.version,
                       effective_from=x.effective_from, effective_to=x.effective_to,
                       content=x.content, parser_version=x.parser_version)


@router.get("/sources/effective")
def sources_effective(as_of: str):
    return {"as_of": as_of, "snapshots": sr.effective_at(as_of)}


@router.post("/market-access/check", status_code=201)
def market_access_check(x: CheckIn):
    if not x.as_of:
        raise HTTPException(422, "as_of is required for reproducible decisions")
    obligations = list(x.obligations) + _auto_obligations(x.cbam_payload, x.taric_payload, x.as_of)
    if not obligations:
        obligations = [{"obligation_id": "NO_OBLIGATIONS", "applicable": True,
                        "status": "MISSING", "reasons": ["no obligations evaluated"],
                        "severity": "BLOCKING", "required_for_release": True,
                        "schema_version": SCHEMA_VERSION}]
    for o in obligations:
        o.setdefault("schema_version", SCHEMA_VERSION)
    decision = de.build_decision(x.transaction_ref, obligations, as_of=x.as_of,
                                 source_snapshot_refs=x.source_snapshot_refs,
                                 evidence_snapshot_refs=x.evidence_snapshot_refs,
                                 predecessor_id=x.predecessor_id)
    de.persist_decision(decision)
    return decision


@router.get("/decisions/{decision_id}")
def get_decision(decision_id: str):
    d = de.get_decision(decision_id)
    if not d:
        raise HTTPException(404, "decision not found")
    return d


@router.post("/decisions/{decision_id}/replay", status_code=201)
def replay_decision(decision_id: str):
    try:
        return de.replay_decision(decision_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except AssertionError as e:
        raise HTTPException(409, f"replay diverged: {e}")


@router.get("/impact")
def portfolio_impact():
    """Gross vs unique blocked value across persisted BLOCKED decisions (§5.13)."""
    from . import revenue_impact as ri
    with connect() as conn:
        try:
            decs = rows(conn, "SELECT payload_json FROM canonical_decisions WHERE status='BLOCKED'")
        except Exception:
            decs = []
    txns, fails = [], []
    for r in decs:
        d = json.loads(r["payload_json"])
        ref = d.get("transaction_ref", "")
        txns.append({"id": ref, "line_value": 0.0})
        for o in d.get("obligation_results", []):
            if o.get("status") in ("FAIL", "MISSING", "STALE", "ERROR"):
                fails.append({"issue_ref": o.get("obligation_id", "?"),
                              "transaction_ids": [ref]})
    # enrich values from canonical_transactions
    with connect() as conn:
        for t in txns:
            try:
                hit = row(conn, "SELECT payload_json FROM canonical_transactions WHERE transaction_ref=?",
                            (t["id"],))
                if hit:
                    t["line_value"] = float(json.loads(hit["payload_json"]).get("line_value", 0))
            except Exception:
                pass
    return ri.compute_impact(txns, fails)


@router.get("/remediation")
def remediation_queue(objective: str = "unlock_value"):
    """Remediation actions derived from BLOCKED decisions, ranked by objective."""
    from . import revenue_impact as ri
    with connect() as conn:
        try:
            decs = rows(conn, "SELECT payload_json FROM canonical_decisions WHERE status='BLOCKED'")
        except Exception:
            decs = []
    by_issue: dict[str, set] = {}
    for r in decs:
        d = json.loads(r["payload_json"])
        for o in d.get("obligation_results", []):
            if o.get("status") in ("FAIL", "MISSING", "STALE", "ERROR"):
                by_issue.setdefault(o.get("obligation_id", "?"), set()).add(d.get("transaction_ref"))
    actions = []
    with connect() as conn:
        for issue, refs in by_issue.items():
            txns = []
            for ref in refs:
                val = 0.0
                try:
                    hit = row(conn, "SELECT payload_json FROM canonical_transactions WHERE transaction_ref=?", (ref,))
                    if hit:
                        val = float(json.loads(hit["payload_json"]).get("line_value", 0))
                except Exception:
                    pass
                txns.append({"id": ref, "line_value": val})
            a = de.build_remediation_action(issue, f"resolve {issue}", "compliance",
                                            txns, objective=objective)
            actions.append(a)
    return ri.rank_actions(actions, objective=objective)


internal = APIRouter(prefix="/internal", tags=["internal"])


@internal.post("/benchmarks/run")
def run_benchmarks(suite: str | None = None):
    """Trigger: runs pytest benchmark suites synchronously, returns summary."""
    import subprocess, sys
    target = ["tests/benchmarks"] if suite is None else [f"tests/benchmarks/test_{suite.lower()}.py"]
    p = subprocess.run([sys.executable, "-m", "pytest", *target, "-q", "--tb=short"],
                       capture_output=True, text=True, cwd=str(__import__("pathlib").Path(__file__).resolve().parents[1]))
    return {"suite": suite or "all", "returncode": p.returncode,
            "stdout_tail": p.stdout[-4000:], "stderr_tail": p.stderr[-2000:]}


@internal.get("/benchmarks/runs")
def list_benchmark_runs(suite_id: str | None = None, limit: int = 50):
    with connect() as conn:
        try:
            if suite_id:
                return rows(conn, "SELECT run_id,suite_id,case_id,result,code_commit,schema_version,"
                                  "decision_id,duration_ms,generated_at,artifact_path FROM benchmark_runs"
                                  " WHERE suite_id=? ORDER BY generated_at DESC LIMIT ?",
                            (suite_id, limit))
            return rows(conn, "SELECT run_id,suite_id,case_id,result,code_commit,schema_version,"
                              "decision_id,duration_ms,generated_at,artifact_path FROM benchmark_runs"
                              " ORDER BY generated_at DESC LIMIT ?", (limit,))
        except Exception:
            return []
