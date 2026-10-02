"""CARBMEE-SUPPLIER (P1, COMPETITIVE-SCENARIO): ERP↔supplier reconciliation (§5.10).

CSV/API-shaped ERP fixtures + supplier/installations with deliberate
identifier inconsistencies. Deterministic identity rules + unresolved queue.
Gaps linked to synthetic orders. No silent merges; completeness reconciles;
order count/value reconciles; supplier→obligation→order→customer lineage
queryable.
"""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from app.benchmark_harness import BenchmarkCase
from app.identity_resolution import resolve

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "tests" / "fixtures" / "carbmee_supplier"
AS_OF = "2026-08-28"

ERP_CSV = """po_line,erp_supplier_name,installation_ref,product_cn,qty_t,line_value_eur,customer
PO-001/1,JSW Steel Vijayanagar,INST-JSW-VJ-01,72083900,100,170000,Customer-NL
PO-002/1,jsw steel vijayanagar ,INST-JSW-VJ-01,72083900,50,85000,Customer-DE
PO-003/1,Demo Ferroalloys,INST-DEMO-01,72083900,20,34000,Customer-IT
PO-004/1,Unknown Traders LLC,INST-UNK-09,72083900,10,17000,Customer-FR
PO-005/1,J S W Steel (Vijayanagar),INST-JSW-VJ-01,72083900,30,51000,Customer-BE
"""

SUPPLIERS = [
    {"supplier_id": "SUP-JSW", "legal_name": "JSW Steel Vijayanagar"},
    {"supplier_id": "SUP-DEMO", "legal_name": "Demo Ferroalloys"},
]
ALIASES = {"jsw steel vijayanagar": "SUP-JSW"}  # exact/alias only; LLC stays queued


def test_carbmee_reconciliation():
    case = BenchmarkCase(suite_id="CARBMEE-SUPPLIER", case_id="erp_link_001",
                         evidence_class="COMPETITIVE-SCENARIO", as_of=AS_OF)
    FIX.mkdir(parents=True, exist_ok=True)
    (FIX / "erp_export.csv").write_text(ERP_CSV)
    rows = list(csv.DictReader(io.StringIO(ERP_CSV)))
    assert len(rows) == 5

    out = resolve(SUPPLIERS, [r["erp_supplier_name"] for r in rows], aliases=ALIASES)
    linked_names = {l["erp_name"] for l in out["linked"]}
    queued_names = {q["erp_name"] for q in out["unresolved_queue"]}
    # _norm strips punctuation/spacing, so all three JSW variants
    # (incl. "J S W Steel (Vijayanagar)") link via EXACT_OR_ALIAS.
    # Only "Unknown Traders LLC" stays queued — no silent merge.
    assert all(l["auto_merged"] and l["rule"] == "EXACT_OR_ALIAS" for l in out["linked"])
    assert all(not q["auto_merged"] and q["owner_role"] for q in out["unresolved_queue"])

    # evidence completeness reconciles to underlying requirements
    total = len(rows)
    assert out["completeness"] == {"erp_names": total, "linked": len(out["linked"]),
                                   "unresolved": len(out["unresolved_queue"])}

    # affected orders reconcile: linked vs gapped line values
    by_name = {}
    for r in rows:
        by_name.setdefault(r["erp_supplier_name"], []).append(float(r["line_value_eur"]))
    gapped_value = sum(v for n, vs in by_name.items() if n in queued_names for v in vs)
    linked_value = sum(v for n, vs in by_name.items() if n in linked_names for v in vs)
    assert round(gapped_value + linked_value, 2) == round(
        sum(float(r["line_value_eur"]) for r in rows), 2)

    # lineage queryable: supplier → orders → customers
    lineage = {l["supplier_id"]: sorted(
        {r["customer"] for r in rows if r["erp_supplier_name"] == l["erp_name"]})
        for l in out["linked"]}
    (FIX / "lineage.json").write_text(json.dumps(lineage, indent=2, sort_keys=True))

    case.assert_and_emit(
        {"erp_lines": total, "linked": len(out["linked"]),
         "unresolved": len(out["unresolved_queue"]),
         "unknown_queued": "Unknown Traders LLC" in queued_names,
         "value_reconciles": True,
         "lineage_suppliers": sorted(lineage)},
        {"erp_lines": 5, "linked": 4, "unresolved": 1,
         "unknown_queued": True, "value_reconciles": True,
         "lineage_suppliers": ["SUP-DEMO", "SUP-JSW"]})
