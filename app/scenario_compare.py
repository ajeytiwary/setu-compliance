"""Scenario comparison (§5.4 SPAETER-STYLE): immutable branches from one RFQ.

Each option is an immutable snapshot; comparing never mutates source/master
data. No procurement recommendation unless a configured objective/constraint
defines the selection logic. Measured/regulatory values are kept separate
from synthetic commercial assumptions.
"""
from __future__ import annotations
import copy

def branch_scenario(rfq: dict, option_id: str, overrides: dict) -> dict:
    snap = copy.deepcopy(rfq)
    snap["option_id"] = option_id
    for k, v in overrides.items():
        snap[k] = v
    snap["immutable"] = True
    return snap


def compare_options(options: list[dict], *, buyer_carbon_threshold: float | None = None,
                    objective: dict | None = None) -> dict:
    """options: [{option_id, material_cost_eur, cbam_exposure_eur, trade_measure_duty_eur,
    evidence_completeness_pct, carbon_intensity_tco2_per_t, assumptions{...}, measured{...}}]."""
    rows = []
    for o in options:
        landed = (float(o.get("material_cost_eur", 0)) + float(o.get("cbam_exposure_eur", 0))
                  + float(o.get("trade_measure_duty_eur", 0)))
        passes = (buyer_carbon_threshold is None
                  or float(o.get("carbon_intensity_tco2_per_t", 0)) <= buyer_carbon_threshold)
        rows.append({**o, "comparable_landed_compliance_cost_eur": round(landed, 2),
                     "buyer_threshold_pass": passes,
                     "unresolved_checks": o.get("unresolved_checks", [])})
    out = {"options": rows,
           "assumptions_separated": True,
           "notice": "Commercial assumptions are synthetic and shown separately from measured/regulatory values."}
    if objective:
        key = objective.get("minimize", "comparable_landed_compliance_cost_eur")
        eligible = [r for r in rows if r["buyer_threshold_pass"]]
        if eligible:
            best = min(eligible, key=lambda r: float(r.get(key, 0)))
            out["selection"] = {"objective": objective, "selected_option": best["option_id"],
                                "key": key}
        else:
            out["selection"] = {"objective": objective, "selected_option": None,
                                "reason": "no option passes buyer constraints"}
    else:
        out["selection"] = {"selected_option": None,
                            "reason": "no configured objective - comparison only, no recommendation"}
    return out
