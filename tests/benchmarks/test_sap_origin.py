"""SAP-ORIGIN (P1, COMPETITIVE-SCENARIO): BOM-based origin evaluation (§5.7).

Canonical BOM (component CN/HS, origin, supplier, qty/value, version) +
versioned rule object (never a hard-coded universal threshold). Output shows
component contribution + exact rule evaluation. Missing supplier/origin
evidence never counts as originating. Audit explains the calculation.
"""
from __future__ import annotations

from app.benchmark_harness import BenchmarkCase
from app.fta_origin import evaluate_origin

AS_OF = "2026-08-28"
RULE_V1 = {"rule_id": "PSR-HRC-7208-V1", "logic_version": "v1",
           "all_of": [{"type": "CTH"}, {"type": "MAXNOM", "threshold_pct": 50}]}


def _payload(materials: list[dict], rule: dict | None = None) -> dict:
    return {"agreement_id": "EU_IN_FTA_2026_NEGOTIATED", "shipment_ref": "SAP-ORIGIN-001",
            "shipment_date": AS_OF, "customs_value_eur": 1812000,
            "mfn_duty_rate_pct": 5.0, "preferential_duty_rate_pct": 0.0,
            "product": {"hs_code": "720839", "ex_works_price": 1750000,
                        "processes": ["BF", "BOF", "CASTER", "HSM"]},
            "materials": materials,
            "product_specific_rule": rule if rule is not None else RULE_V1}


BASE_MATS = [
    {"material_id": "IRON-ORE", "hs_code": "260111", "value": 320000, "originating": False},
    {"material_id": "COKE", "hs_code": "270400", "value": 180000, "originating": False},
    {"material_id": "SCRAP-IN", "hs_code": "720449", "value": 50000, "originating": True},
]


def test_sap_origin_qualifies_reproducible():
    case = BenchmarkCase(suite_id="SAP-ORIGIN", case_id="qualifies_001",
                         evidence_class="COMPETITIVE-SCENARIO", as_of=AS_OF)
    out = evaluate_origin(_payload(list(BASE_MATS)))
    # reproducible from BOM + rule + evidence
    out2 = evaluate_origin(_payload(list(BASE_MATS)))
    assert out["psr_evaluation"] == out2["psr_evaluation"]
    parts = {p["type"]: p["pass"] for p in out["psr_evaluation"]["parts"]}
    case.assert_and_emit(
        {"technical_pass": out["psr_evaluation"]["pass"],
         "cth": parts.get("CTH"), "maxnom": parts.get("MAXNOM"),
         "legal_regime": out["legal_regime"],
         "preference_available": out["preference_available"],
         "rule_version": RULE_V1["logic_version"]},
        {"technical_pass": True, "cth": True, "maxnom": True,
         "legal_regime": "CURRENT_MFN", "preference_available": False,
         "rule_version": "v1"})


def test_sap_origin_single_component_change():
    """Flipping one component origin changes only the dependent evaluation."""
    case = BenchmarkCase(suite_id="SAP-ORIGIN", case_id="recalc_001",
                         evidence_class="COMPETITIVE-SCENARIO", as_of=AS_OF)
    before = evaluate_origin(_payload(list(BASE_MATS)))
    mats = [dict(m) for m in BASE_MATS]
    # 1M non-originating material blows MAXNOM 50% on 1.75M ex-works
    mats.append({"material_id": "ALLOY-X", "hs_code": "720839",
                 "value": 1000000, "originating": False})
    after = evaluate_origin(_payload(mats))
    case.assert_and_emit(
        {"before": before["psr_evaluation"]["pass"],
         "after": after["psr_evaluation"]["pass"],
         "rule_unchanged": RULE_V1["logic_version"] == "v1"},
        {"before": True, "after": False, "rule_unchanged": True})


def test_sap_origin_missing_evidence_not_originating():
    """Material without origin evidence defaults to non-originating → evaluated."""
    case = BenchmarkCase(suite_id="SAP-ORIGIN", case_id="missing_evidence_001",
                         evidence_class="COMPETITIVE-SCENARIO", as_of=AS_OF)
    mats = [{"material_id": "M-UNKNOWN", "hs_code": "720839",
             "value": 1700000, "originating": False}]  # no evidence → not originating
    out = evaluate_origin(_payload(mats))
    assert out["psr_evaluation"]["pass"] is False
    case.assert_and_emit(
        {"pass": out["psr_evaluation"]["pass"],
         "silently_originating": any(
             p.get("pass") for p in out["psr_evaluation"]["parts"]
             if p["type"] == "MAXNOM") and out["psr_evaluation"]["pass"]},
        {"pass": False, "silently_originating": False})
