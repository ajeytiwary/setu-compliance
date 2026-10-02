"""REVENUE-IMPACT (P1, SYNTHETIC): non-double-counted exposure (§5.13).

Overlapping failures (one order blocked by multiple issues). Gross vs unique
tracked separately. Removing one issue recomputes residual correctly. Action
ranking reproducible with exposed formula/inputs; never a bare recommendation.
"""
from __future__ import annotations

from app import revenue_impact as ri
from app.benchmark_harness import BenchmarkCase

AS_OF = "2026-08-28"

TXNS = [
    {"id": "TXN-R1", "line_value": 1700000.0},  # blocked by CBAM + QUOTA
    {"id": "TXN-R2", "line_value": 850000.0},   # blocked by CBAM only
    {"id": "TXN-R3", "line_value": 340000.0},   # blocked by QUOTA only
]
FAILURES = [
    {"issue_ref": "CBAM_EMISSIONS", "transaction_ids": ["TXN-R1", "TXN-R2"]},
    {"issue_ref": "TARIFF_QUOTA", "transaction_ids": ["TXN-R1", "TXN-R3"]},
]


def test_revenue_impact_no_double_count():
    case = BenchmarkCase(suite_id="REVENUE-IMPACT", case_id="overlap_001",
                         evidence_class="SYNTHETIC", as_of=AS_OF)
    impact = ri.compute_impact(TXNS, FAILURES)
    # gross double-counts R1; unique counts it once
    assert impact["gross_affected_value"] == 1700000 * 2 + 850000 + 340000
    assert impact["unique_blocked_value"] == 1700000 + 850000 + 340000
    assert impact["double_counted_value"] == 1700000.0

    residual = ri.residual_after_fix(TXNS, FAILURES, "TARIFF_QUOTA")
    assert residual["unique_blocked_transactions"] == ["TXN-R1", "TXN-R2"]
    assert residual["unique_blocked_value"] == 2550000.0

    actions = [
        {"action_id": "A1", "issue_ref": "CBAM_EMISSIONS",
         "unlock_value": 2550000.0, "effort_weight": 2.0},
        {"action_id": "A2", "issue_ref": "TARIFF_QUOTA",
         "unlock_value": 2040000.0, "effort_weight": 1.0},
    ]
    ranked = ri.rank_actions(actions, objective="unlock_value")
    assert ranked["objective"] == "unlock_value"
    assert ranked["actions"][0]["action_id"] == "A2"  # 2.04M/1 > 2.55M/2
    assert all("formula" in a and "inputs" in a for a in ranked["actions"])
    case.assert_and_emit(
        {"gross": impact["gross_affected_value"],
         "unique": impact["unique_blocked_value"],
         "double_counted": impact["double_counted_value"],
         "residual_unique": residual["unique_blocked_value"],
         "top_action": ranked["actions"][0]["action_id"],
         "objective_exposed": ranked["objective"]},
        {"gross": 4590000.0, "unique": 2890000.0, "double_counted": 1700000.0,
         "residual_unique": 2550000.0, "top_action": "A2",
         "objective_exposed": "unlock_value"})
