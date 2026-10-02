"""Canonical trade/evidence data model + decision policy (§3, §6 of benchmark-suite spec).

One canonical model used by ALL benchmark suites. Implemented as Pydantic v2
models (JSON Schema exportable) with schema_version persisted on every object.
"""
from __future__ import annotations
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import uuid4
import hashlib, json

SCHEMA_VERSION = "EUROSETU_CANONICAL_V1"
CODE_COMMIT = "unknown"  # stamped by CI via env EUROSETU_CODE_COMMIT

# ---------------------------------------------------------------- statuses

class TxnStatus(str, Enum):
    READY = "READY"
    CONDITIONAL = "CONDITIONAL"
    BLOCKED = "BLOCKED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    ERROR = "ERROR"

class EvidenceState(str, Enum):
    VALID = "VALID"
    STALE = "STALE"
    EXPIRED = "EXPIRED"
    SUPERSEDED = "SUPERSEDED"
    CONFLICTING = "CONFLICTING"
    UNVERIFIED = "UNVERIFIED"
    MISSING = "MISSING"

class EvidenceClass(str, Enum):
    NORMATIVE = "NORMATIVE"
    EXTERNAL_ORACLE = "EXTERNAL-ORACLE"
    COMPETITIVE_SCENARIO = "COMPETITIVE-SCENARIO"
    SYNTHETIC = "SYNTHETIC"

class ObligationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    MISSING = "MISSING"
    STALE = "STALE"
    UNVERIFIED = "UNVERIFIED"
    CONFLICTING = "CONFLICTING"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    ERROR = "ERROR"

try:
    from pydantic import BaseModel, Field

    class _Base(BaseModel):
        schema_version: str = SCHEMA_VERSION

    class TradeTransaction(_Base):
        id: str = Field(default_factory=lambda: str(uuid4()))
        order_id: str = ""
        shipment_id: str = ""
        line_id: str = ""
        seller: str = ""
        buyer: str = ""
        importer: str = ""
        origin_country: str = "IN"
        destination_country: str = "NL"
        shipment_date: str = "2026-08-28"
        currency: str = "EUR"
        line_value: float = 0.0
        quantity: float = 0.0
        unit: str = "t"

    class Product(_Base):
        product_id: str = Field(default_factory=lambda: str(uuid4()))
        sku: str = ""
        description: str = ""
        cn_code: str = ""
        cn_version: str = "2026"
        material_family: str = "steel"
        bom_id: str | None = None

    class Facility(_Base):
        facility_id: str = Field(default_factory=lambda: str(uuid4()))
        operator_id: str = ""
        country: str = "IN"
        address_ref: str = ""
        installation_id: str | None = None
        production_route: str | None = None
        validity: dict | None = None

    class Supplier(_Base):
        supplier_id: str = Field(default_factory=lambda: str(uuid4()))
        legal_name: str = ""
        country: str = "IN"
        identifiers: dict = Field(default_factory=dict)
        parent_refs: list[str] = Field(default_factory=list)

    class BOMComponent(BaseModel):
        product_material: str = ""
        qty: float = 0.0
        value: float = 0.0
        origin: str = ""
        supplier: str = ""

    class BOM(_Base):
        bom_id: str = Field(default_factory=lambda: str(uuid4()))
        product_id: str = ""
        version: str = "1"
        valid_from: str | None = None
        valid_to: str | None = None
        components: list[BOMComponent] = Field(default_factory=list)

    class EvidenceObject(_Base):
        evidence_id: str = Field(default_factory=lambda: str(uuid4()))
        type: str = ""
        subject_ref: str = ""
        issuer: str = ""
        source_uri_ref: str = ""
        content_hash: str = ""
        collected_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
        valid_from: str | None = None
        valid_to: str | None = None
        verification_status: str = "UNVERIFIED"
        supersedes: str | None = None
        confidentiality: str = "internal"

    class RegulatorySourceSnapshot(_Base):
        source_id: str = ""
        authority: str = ""
        title: str = ""
        legal_basis: list[str] = Field(default_factory=list)
        version: str = ""
        retrieved_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
        effective_from: str | None = None
        effective_to: str | None = None
        content_hash: str = ""
        parser_version: str = "v1"

    class Rule(_Base):
        rule_id: str = ""
        family: str = ""
        jurisdiction: str = "EU"
        product_scope: list[str] = Field(default_factory=list)
        geography_scope: list[str] = Field(default_factory=list)
        effective_from: str | None = None
        effective_to: str | None = None
        source_refs: list[str] = Field(default_factory=list)
        severity: Literal["BLOCKING", "CONDITIONAL", "INFO"] = "BLOCKING"
        required_evidence: list[str] = Field(default_factory=list)
        logic_version: str = "v1"

    class ObligationResult(_Base):
        obligation_id: str = ""
        applicable: bool = True
        status: str = "PASS"
        reasons: list[str] = Field(default_factory=list)
        evidence_refs: list[str] = Field(default_factory=list)
        rule_refs: list[str] = Field(default_factory=list)
        calculation_refs: list[str] = Field(default_factory=list)
        severity: str = "BLOCKING"
        required_for_release: bool = True

    class Decision(_Base):
        decision_id: str = Field(default_factory=lambda: str(uuid4()))
        transaction_ref: str = ""
        as_of: str = Field(default_factory=lambda: date.today().isoformat())
        status: str = "ERROR"
        obligation_results: list[dict] = Field(default_factory=list)
        blocking_reasons: list[str] = Field(default_factory=list)
        source_snapshot_refs: list[dict] = Field(default_factory=list)
        evidence_snapshot_refs: list[str] = Field(default_factory=list)
        decision_hash: str = ""
        predecessor_id: str | None = None
        policy_version: str = "DECISION_POLICY_V1"

    class RemediationAction(_Base):
        action_id: str = Field(default_factory=lambda: str(uuid4()))
        issue_ref: str = ""
        owner_role: str = ""
        requested_evidence_action: str = ""
        priority: int = 0
        affected_transactions: list[str] = Field(default_factory=list)
        unlock_value: float = 0.0
        marginal_unlock_value: float = 0.0
        prerequisites: list[str] = Field(default_factory=list)
        confidence: str | None = None
        source_refs: list[str] = Field(default_factory=list)
        evidence_refs: list[str] = Field(default_factory=list)

    def model_json_schema(name: str) -> dict:
        m = {"TradeTransaction": TradeTransaction, "Product": Product,
             "Facility": Facility, "Supplier": Supplier, "BOM": BOM,
             "EvidenceObject": EvidenceObject,
             "RegulatorySourceSnapshot": RegulatorySourceSnapshot,
             "Rule": Rule, "ObligationResult": ObligationResult,
             "Decision": Decision, "RemediationAction": RemediationAction}[name]
        return m.model_json_schema()

except ImportError:  # pragma: no cover - pydantic always present in practice
    pass


def canonical_hash(obj: dict) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def decision_hash(decision: dict) -> str:
    core = {k: v for k, v in decision.items()
            if k not in ("decision_id", "decision_hash", "generated_at", "code_commit")}
    return canonical_hash(core)
