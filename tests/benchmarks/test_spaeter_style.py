"""SPAETER-STYLE (P2, COMPETITIVE-SCENARIO): sourcing-option comparison (§5.4).

Each option an immutable branch from one RFQ. No procurement recommendation
without a configured objective/constraint. Measured/regulatory values kept
separate from synthetic commercial assumptions.
"""
from __future__ import annotations

from app.benchmark_harness import BenchmarkCase
from app.scenario_compare import branch_scenario, compare_options

AS_OF = "2026-08-28"

RFQ = {"rfq_id": "RFQ-HRC-001", "product_cn": "72083900", "qty_t": 100,
       "destination": "DE", "measured": {"benchmark_tco2_per_t": 0.044}}


def _options() -> list[dict]:
    a = branch_scenario(RFQ, "OPT-A-IN", {
        "material_cost_eur": 150000.0, "cbam_exposure_eur": 12000.0,
        "trade_measure_duty_eur": 7500.0, "evidence_completeness_pct": 100.0,
        "carbon_intensity_tco2_per_t": 1.73, "unresolved_checks": [],
        "measured": {"see_tco2_per_t": 1.73},
        "assumptions": {"freight_eur": 4000.0, "synthetic": True}})
    b = branch_scenario(RFQ, "OPT-B-TR", {
        "material_cost_eur": 145000.0, "cbam_exposure_eur": 9000.0,
        "trade_measure_duty_eur": 7500.0, "evidence_completeness_pct": 60.0,
        "carbon_intensity_tco2_per_t": 2.10, "unresolved_checks": ["ORIGIN"],
        "measured": {"see_tco2_per_t": 2.10},
        "assumptions": {"freight_eur": 3500.0, "synthetic": True}})
    return [a, b]


def test_spaeter_comparison_no_recommendation_by_default():
    case = BenchmarkCase(suite_id="SPAETER-STYLE", case_id="compare_001",
                         evidence_class="COMPETITIVE-SCENARIO", as_of=AS_OF)
    before = dict(RFQ)
    out = compare_options(_options(), buyer_carbon_threshold=2.0)
    by_id = {o["option_id"]: o for o in out["options"]}
    case.assert_and_emit(
        {"a_landed": by_id["OPT-A-IN"]["comparable_landed_compliance_cost_eur"],
         "a_pass": by_id["OPT-A-IN"]["buyer_threshold_pass"],
         "b_pass": by_id["OPT-B-TR"]["buyer_threshold_pass"],
         "b_unresolved": by_id["OPT-B-TR"]["unresolved_checks"],
         "selection": out["selection"]["selected_option"],
         "rfq_unmutated": RFQ == before,
         "assumptions_separated": out["assumptions_separated"]},
        {"a_landed": 169500.0, "a_pass": True, "b_pass": False,
         "b_unresolved": ["ORIGIN"], "selection": None,
         "rfq_unmutated": True, "assumptions_separated": True})


def test_spaeter_selection_with_objective():
    case = BenchmarkCase(suite_id="SPAETER-STYLE", case_id="select_001",
                         evidence_class="COMPETITIVE-SCENARIO", as_of=AS_OF)
    out = compare_options(_options(), buyer_carbon_threshold=2.0,
                          objective={"minimize": "comparable_landed_compliance_cost_eur"})
    case.assert_and_emit(
        {"selected": out["selection"]["selected_option"],
         "objective": out["selection"]["objective"]},
        {"selected": "OPT-A-IN",
         "objective": {"minimize": "comparable_landed_compliance_cost_eur"}})
