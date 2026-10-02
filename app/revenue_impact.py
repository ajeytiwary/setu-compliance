"""Revenue impact (§5.13): gross vs unique blocked value, no double counting.

Overlapping failures: one order blocked by multiple issues counts once in the
unique total. Removing one issue recomputes the residual correctly. Action
ranking uses an explicit configurable objective (default unlock_value) and
exposes formula + inputs — never a bare 'recommended' label.
"""
from __future__ import annotations

OBJECTIVE_DEFAULT = "unlock_value"


def compute_impact(transactions: list[dict], failures: list[dict]) -> dict:
    """transactions: [{id, line_value}]; failures: [{issue_ref, transaction_ids[]}]."""
    by_id = {t["id"]: float(t.get("line_value", t.get("value_eur", 0))) for t in transactions}
    gross = sum(by_id[tid] for f in failures for tid in f.get("transaction_ids", []) if tid in by_id)
    blocked_ids = {tid for f in failures for tid in f.get("transaction_ids", []) if tid in by_id}
    unique = sum(by_id[tid] for tid in blocked_ids)
    per_issue = [{"issue_ref": f["issue_ref"],
                  "affected_transactions": [t for t in f.get("transaction_ids", []) if t in by_id],
                  "gross_affected_value": round(sum(by_id[t] for t in f.get("transaction_ids", []) if t in by_id), 2)}
                 for f in failures]
    return {"gross_affected_value": round(gross, 2),
            "unique_blocked_value": round(unique, 2),
            "unique_blocked_transactions": sorted(blocked_ids),
            "double_counted_value": round(gross - unique, 2),
            "per_issue": per_issue}


def residual_after_fix(transactions: list[dict], failures: list[dict], fixed_issue_ref: str) -> dict:
    remaining = [f for f in failures if f["issue_ref"] != fixed_issue_ref]
    out = compute_impact(transactions, remaining)
    out["fixed_issue"] = fixed_issue_ref
    return out


def rank_actions(actions: list[dict], objective: str = OBJECTIVE_DEFAULT) -> dict:
    """actions: [{action_id, issue_ref, unlock_value, effort_weight?}]."""
    ranked = []
    for a in actions:
        effort = float(a.get("effort_weight", 1.0)) or 1.0
        score = float(a.get("unlock_value", 0)) / effort
        ranked.append({**a, "score": round(score, 2),
                       "formula": "unlock_value / effort_weight",
                       "inputs": {"unlock_value": a.get("unlock_value", 0), "effort_weight": effort}})
    ranked.sort(key=lambda x: x["score"], reverse=True)
    return {"objective": objective,
            "formula": "unlock_value / effort_weight (descending)",
            "actions": ranked,
            "notice": "Ranking is reproducible from the exposed formula and inputs; "
                      "no action is presented as legal advice."}
