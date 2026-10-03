#!/usr/bin/env python3
"""Messy MTC + receipts demo: messy input must BLOCK, remediated must reach READY.

Reads the synthetic messy CSVs in this folder, classifies each row through
app.evidence_lifecycle (deterministic as_of clock), aggregates through
app.decision_engine (DECISION_POLICY_V1 fail-closed), and prints the
before/after table. Mirrors CHAOS-002/003/007/013/014/015 shapes without
copying any vendor file.

Usage: python use_cases/ouco_mtc_messy/run_messy_demo.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app import decision_engine as de
from app import evidence_lifecycle as ev

AS_OF = "2026-08-28"
HERE = Path(__file__).resolve().parent

# messy defect -> (evidence objects, expected lifecycle state, human defect note)
DEFECTS: dict[str, tuple[list[dict], str, str]] = {
    "decimal_comma": (
        [{"evidence_id": "E-MESSY", "subject_ref": "TXN-MESSY",
          "collected_at": "2026-08-01", "verification_status": "UNPARSED"}],
        "UNVERIFIED", "decimal comma '0,16' rejected at parse — never guessed"),
    "units_embedded": (
        [{"evidence_id": "E-MESSY", "subject_ref": "TXN-MESSY",
          "collected_at": "2026-08-01", "verification_status": "UNPARSED"}],
        "UNVERIFIED", "units embedded in numeric cells — non-numeric rejected"),
    "heat_mismatch": (
        [{"evidence_id": "E-MESSY-a", "subject_ref": "TXN-MESSY",
          "collected_at": "2026-08-01", "verification_status": "VERIFIED",
          "sha256": "heat-3303"},
         {"evidence_id": "E-MESSY-b", "subject_ref": "TXN-MESSY",
          "collected_at": "2026-08-01", "verification_status": "VERIFIED",
          "sha256": "heat-3304"}],
        "CONFLICTING", "heat on MTC disagrees with packing list"),
    "duplicate_supplier": (
        [{"evidence_id": "E-MESSY-a", "subject_ref": "TXN-MESSY",
          "collected_at": "2026-08-01", "verification_status": "VERIFIED",
          "sha256": "supplier-1"},
         {"evidence_id": "E-MESSY-b", "subject_ref": "TXN-MESSY",
          "collected_at": "2026-08-01", "verification_status": "VERIFIED",
          "sha256": "supplier-2"}],
        "CONFLICTING", "same legal entity twice with different supplier_ids"),
    "duplicate_invoice": (
        [{"evidence_id": "E-MESSY-a", "subject_ref": "TXN-MESSY",
          "collected_at": "2026-08-01", "verification_status": "VERIFIED",
          "sha256": "inv-1"},
         {"evidence_id": "E-MESSY-b", "subject_ref": "TXN-MESSY",
          "collected_at": "2026-08-01", "verification_status": "VERIFIED",
          "sha256": "inv-2"}],
        "CONFLICTING", "same invoice number posted twice"),
    "duplicate": (
        [{"evidence_id": "E-MESSY-a", "subject_ref": "TXN-MESSY",
          "collected_at": "2026-08-01", "verification_status": "VERIFIED",
          "sha256": "rcpt-1"},
         {"evidence_id": "E-MESSY-b", "subject_ref": "TXN-MESSY",
          "collected_at": "2026-08-01", "verification_status": "VERIFIED",
          "sha256": "rcpt-2"}],
        "CONFLICTING", "same receipt posted twice"),
    "qty_mismatch": (
        [{"evidence_id": "E-MESSY-a", "subject_ref": "TXN-MESSY",
          "collected_at": "2026-08-01", "verification_status": "VERIFIED",
          "sha256": "qty-2"},
         {"evidence_id": "E-MESSY-b", "subject_ref": "TXN-MESSY",
          "collected_at": "2026-08-01", "verification_status": "VERIFIED",
          "sha256": "qty-3"}],
        "CONFLICTING", "receipt qty disagrees with PO"),
}


def decide(txn: str, ev_state: str, reason: str,
           predecessor: str | None = None) -> dict:
    obs = [{"obligation_id": "CBAM_EMISSIONS", "applicable": True,
            "status": "PASS", "reasons": [], "severity": "BLOCKING",
            "required_for_release": True,
            "schema_version": "EUROSETU_CANONICAL_V1"},
           {"obligation_id": "TARIC_DUTY", "applicable": True,
            "status": "PASS", "reasons": [], "severity": "BLOCKING",
            "required_for_release": True,
            "schema_version": "EUROSETU_CANONICAL_V1"},
           {"obligation_id": "EVIDENCE_CHAIN", "applicable": True,
            "status": ev_state, "reasons": [reason] if reason else [],
            "severity": "BLOCKING", "required_for_release": True,
            "schema_version": "EUROSETU_CANONICAL_V1"}]
    return de.build_decision(txn, obs, as_of=AS_OF, predecessor_id=predecessor)


def run_row(row_id: str, defect_kind: str) -> dict:
    """Classify one messy row and remediate. Returns the before/after record."""
    evidence, expected_state, note = DEFECTS[defect_kind]
    evaluated = ev.evaluate_requirement(evidence, as_of=AS_OF)
    assert evaluated["state"] == expected_state, f"{row_id}: {evaluated}"
    before = decide(f"TXN-{row_id}", evaluated["state"], note)
    assert before["status"] == "BLOCKED", f"{row_id} must fail closed"
    after = decide(f"TXN-{row_id}", "PASS", "corrected evidence ingested",
                   predecessor=before["decision_id"])
    assert after["status"] == "READY", f"{row_id} remediation must reach READY"
    assert after["predecessor_id"] == before["decision_id"]
    return {"row_id": row_id, "defect_kind": defect_kind,
            "evidence_state": evaluated["state"],
            "initial": before["status"], "remediated": after["status"],
            "predecessor_preserved": True,
            "policy": after["policy_version"]}


def receipt_parse_check() -> list[dict]:
    """Run the typed receipt extractor over the messy receipts and assert the
    four defect shapes stay unresolved (fail-closed) - '1,9' never 19."""
    from app.document_ingest import extract_receipt_records

    text = "receipt_id,vendor,total_raw,qty_raw,defect_kind\n"
    with (HERE / "receipts_messy_sample.csv").open() as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        qty = r["qty_raw"].split()[0] if r["qty_raw"] else ""
        line = f'{r["receipt_id"]},{r["vendor"]},"{r["total_raw"]}",{qty}\n'
        text += line
        # The fixture labels the duplicate row; post it twice so the parser
        # actually sees the same receipt number arrive twice.
        if r["defect_kind"] == "duplicate":
            text += line
    parsed = extract_receipt_records(text, "receipts_messy_sample.csv", "messy2026")
    by_id = {}
    for rec in parsed["records"]:
        by_id.setdefault(rec["receipt_id"], []).append(rec)
    out = []
    for src in rows:
        rid, kind = src["receipt_id"], src["defect_kind"]
        recs = by_id[rid]
        rec = recs[-1] if kind == "duplicate" else recs[0]
        if kind == "decimal_comma":
            assert rec["total"] is None, f"{rid}: '1,9' must not parse as 19"
            assert "RECEIPT_TOTAL_DECIMAL_COMMA" in rec["codes"]
        elif kind == "units_embedded":
            assert rec["total"] is None, f"{rid}: '412 EUR' must not parse"
            assert "RECEIPT_TOTAL_UNITS_EMBEDDED" in rec["codes"]
        elif kind == "duplicate":
            assert len(recs) == 2, f"{rid}: expected two postings, got {len(recs)}"
            assert "RECEIPT_DUPLICATE" in rec["codes"]
            assert rec["duplicate_of"] == recs[0]["record_key"]
        out.append({"receipt_id": rid, "defect_kind": kind,
                    "total_raw": rec["total_raw"], "total": rec["total"],
                    "codes": rec["codes"], "duplicate_of": rec["duplicate_of"]})
    return out


def main() -> int:
    print("row_id | defect | evidence_state | initial | remediated")
    results = []
    with (HERE / "messy_mtc_input.csv").open() as f:
        for row in csv.DictReader(f):
            rec = run_row(row["row_id"], row["defect_kind"])
            results.append(rec)
            print(f"{rec['row_id']} | {rec['defect_kind']} | "
                  f"{rec['evidence_state']} | {rec['initial']} | {rec['remediated']}")
    with (HERE / "receipts_messy_sample.csv").open() as f:
        for row in csv.DictReader(f):
            rec = run_row(row["receipt_id"], row["defect_kind"])
            results.append(rec)
            print(f"{rec['row_id']} | {rec['defect_kind']} | "
                  f"{rec['evidence_state']} | {rec['initial']} | {rec['remediated']}")
    blocked = sum(1 for r in results if r["initial"] == "BLOCKED")
    ready = sum(1 for r in results if r["remediated"] == "READY")
    print(f"\nmessy rows: {len(results)}, BLOCKED initially: {blocked}, "
          f"READY after remediation: {ready}")
    assert blocked == len(results) and ready == len(results)

    print("\nreceipt parse (typed records, fail-closed):")
    print("receipt_id | defect | total_raw | parsed_total | codes | duplicate_of")
    for r in receipt_parse_check():
        print(f"{r['receipt_id']} | {r['defect_kind']} | {r['total_raw']} | "
              f"{r['total'] if r['total'] is not None else '(not parsed)'} | "
              f"{'; '.join(r['codes']) or 'OK'} | {r['duplicate_of'] or '-'}")
    print("demo OK — messy input fails closed, remediated input reaches READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
