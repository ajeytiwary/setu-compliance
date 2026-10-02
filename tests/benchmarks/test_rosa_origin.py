"""ROSA-ORIGIN (P1, EXTERNAL-ORACLE): captured-oracle comparison (§5.8).

Scenario inputs + captured oracle output/date stored as fixtures (no live
scraping). ROSA treated as comparison oracle, not legal certification.
Cases span qualifying / non-qualifying / insufficient-information.
Mismatch → diagnostic mapping rule/input divergence; provenance visible.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.benchmark_harness import BenchmarkCase
from app.fta_origin import evaluate_origin

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "tests" / "fixtures" / "rosa_origin"
AS_OF = "2026-08-28"

ORACLES = {
    "qualify_001": {
        "captured_at": "2026-08-20", "provenance": "ROSA self-assessment capture (manual)",
        "input_ref": "hrc_cth_maxnom",
        "oracle": {"technical_origin_preview": True, "legal_regime": "CURRENT_MFN",
                   "preference_available": False},
    },
    "nonqualify_001": {
        "captured_at": "2026-08-20", "provenance": "ROSA self-assessment capture (manual)",
        "input_ref": "hrc_maxnom_fail",
        "oracle": {"technical_origin_preview": False, "legal_regime": "CURRENT_MFN",
                   "preference_available": False},
    },
    "insufficient_001": {
        "captured_at": "2026-08-20", "provenance": "ROSA self-assessment capture (manual)",
        "input_ref": "hrc_no_psr",
        "oracle": {"technical_origin_preview": None, "legal_regime": "CURRENT_MFN",
                   "preference_available": False},
    },
}

INPUTS = {
    "hrc_cth_maxnom": {
        "product": {"hs_code": "720839", "ex_works_price": 1750000,
                    "processes": ["BF", "BOF", "CASTER", "HSM"]},
        "materials": [
            {"material_id": "IRON-ORE", "hs_code": "260111", "value": 320000,
             "originating": False},
            {"material_id": "COKE", "hs_code": "270400", "value": 180000,
             "originating": False},
            {"material_id": "SCRAP-IN", "hs_code": "720449", "value": 50000,
             "originating": True}],
        "product_specific_rule": {"all_of": [{"type": "CTH"},
                                             {"type": "MAXNOM", "threshold_pct": 50}]}},
    "hrc_maxnom_fail": {
        "product": {"hs_code": "720839", "ex_works_price": 1750000,
                    "processes": ["BF", "BOF"]},
        "materials": [{"material_id": "M1", "hs_code": "260111",
                       "value": 1000000, "originating": False}],
        "product_specific_rule": {"all_of": [{"type": "CTH"},
                                             {"type": "MAXNOM", "threshold_pct": 50}]}},
    "hrc_no_psr": {
        "product": {"hs_code": "720839", "ex_works_price": 1750000,
                    "processes": ["BF", "BOF"]},
        "materials": [{"material_id": "M1", "hs_code": "260111",
                       "value": 100000, "originating": False}],
        "product_specific_rule": None},
}


def _run(input_ref: str) -> dict:
    spec = INPUTS[input_ref]
    return evaluate_origin({
        "agreement_id": "EU_IN_FTA_2026_NEGOTIATED", "shipment_ref": f"ROSA-{input_ref}",
        "shipment_date": AS_OF, "customs_value_eur": 1812000,
        "mfn_duty_rate_pct": 5.0, "preferential_duty_rate_pct": 0.0,
        **spec})


def _check(case_id: str):
    FIX.mkdir(parents=True, exist_ok=True)
    (FIX / f"{case_id}.json").write_text(json.dumps(
        ORACLES[case_id], indent=2, sort_keys=True))
    oracle = ORACLES[case_id]["oracle"]
    out = _run(ORACLES[case_id]["input_ref"])
    actual = {"technical_origin_preview": out["technical_origin_preview"],
              "legal_regime": out["legal_regime"],
              "preference_available": out["preference_available"]}
    case = BenchmarkCase(suite_id="ROSA-ORIGIN", case_id=case_id,
                         evidence_class="EXTERNAL-ORACLE", as_of=AS_OF)
    try:
        result = case.assert_and_emit(actual, oracle)
    except AssertionError:
        # diagnostic mapping on divergence (§5.8), then re-raise
        div = {k: {"oracle": oracle.get(k), "actual": actual.get(k)}
               for k in oracle if oracle.get(k) != actual.get(k)}
        raise AssertionError(f"oracle divergence for {case_id}: {div}")
    return result


def test_rosa_qualifying():
    _check("qualify_001")


def test_rosa_non_qualifying():
    _check("nonqualify_001")


def test_rosa_insufficient_information():
    _check("insufficient_001")
