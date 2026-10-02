"""Deterministic identity resolution (§5.10): ERP ↔ supplier ↔ installation.

No silent merges: exact/alias matches link automatically with a recorded rule;
everything else lands in the unresolved-match queue for a human owner.
"""
from __future__ import annotations
import re

def _norm(s: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(s or "").upper())


def resolve(supplier_master: list[dict], erp_names: list[str],
            aliases: dict | None = None) -> dict:
    """supplier_master: [{supplier_id, legal_name}]. Returns links + queue."""
    aliases = aliases or {}
    index = {}
    for s in supplier_master:
        index[_norm(s["legal_name"])] = s["supplier_id"]
        index[_norm(s["supplier_id"])] = s["supplier_id"]
    for alias, sid in (aliases or {}).items():
        index[_norm(alias)] = sid
    linked, queue = [], []
    for name in erp_names:
        sid = index.get(_norm(name))
        if sid:
            linked.append({"erp_name": name, "supplier_id": sid,
                           "rule": "EXACT_OR_ALIAS", "auto_merged": True})
        else:
            # fuzzy hint only - never auto-merge
            hint = next((s["supplier_id"] for s in supplier_master
                         if _norm(name)[:6] and _norm(name)[:6] in _norm(s["legal_name"])), None)
            queue.append({"erp_name": name, "supplier_id": None,
                          "suggested_hint": hint, "auto_merged": False,
                          "owner_role": "procurement",
                          "reason": "no exact/alias match - human confirmation required"})
    return {"linked": linked, "unresolved_queue": queue,
            "completeness": {"erp_names": len(erp_names), "linked": len(linked),
                             "unresolved": len(queue)}}
