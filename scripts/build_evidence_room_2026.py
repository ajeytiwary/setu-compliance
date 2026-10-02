#!/usr/bin/env python3
"""Build the EU-STEEL-EXPORT-2026 evidence room (Layer 4 of the 4-layer corpus).

Layer model (docs/dataset_example_resources.md):
  Layer 1 — authoritative regulatory goldens (EC CBAM examples/defaults/benchmarks,
             operator guidance, TARIC): NORMATIVE oracles, never redistributed.
  Layer 2 — public real-world documents/data (UCI steel telemetry, DocILE/CORD/QUEST,
             worldsteel LCI, voestalpine EPDs, Eurostat COMEXT, UN Comtrade,
             Terlouw Steel_CBAM): real inputs with provenance, never scraped.
  Layer 3 — competitor-derived scenarios (Steelforce/Spaeter/CBAMReturn patterns):
             workflow shapes only, re-implemented synthetically, COMPETITIVE-SCENARIO.
  Layer 4 — deliberately corrupted synthetic client packs (this script): SYNTHETIC,
             deterministic, offline, with parent_artifact pointers to clean originals.

This script reads the deterministic base corpus produced by
scripts/build_public_evidence_corpus.py (evidence_room/transactions.csv etc.)
and materializes the prospect-style folder layout:

  data/public_trade_evidence/EU-STEEL-EXPORT-2026/
    ERP/ sales_orders.csv, purchase_orders.csv, suppliers.csv
    LOGISTICS/ invoices/, packing_lists/, customs_declarations/ (manifests + samples)
    QUALITY/ mill_test_certificates/ (manifest + samples)
    CARBON/ energy_meter.csv, facility_emissions.csv, cbam_supplier_templates/,
            epds/, verification/ (manifests + samples)
    REGULATORY/ taric/, cbam/, sanctions/ (versioned snapshots)
    corrupted_derivatives.json (CHAOS-001..015 with parent pointers)
    expected/ initial_decisions.json, remediation_actions.json, final_decisions.json
    provenance.json (every artifact: source_type/source_url/license/retrieved_at/
                     sha256/original_filename/synthetic_transform/parent_artifact/
                     expected_use)

Offline + deterministic (seed 20261002). No network. No competitor PDFs copied.
Usage: python scripts/build_evidence_room_2026.py [--clean] [--transactions N] [--ems-rows M]
"""
from __future__ import annotations
import argparse, csv, hashlib, json, random
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/public_trade_evidence"
ROOM = BASE / "EU-STEEL-EXPORT-2026"
CFG = ROOT / "config/public_evidence_sources.json"
SEED = 20261002

# CHAOS-001..015 family (CBAMReturn-messy-supplier patterns, re-implemented synthetically).
CHAOS = [
    {"id": "CHAOS-001", "title": "renamed worksheets", "defect": "supplier workbook sheet 'Installation Data' renamed to 'Sheet1 FINAL v3 (2)'",
     "evidence_state": "UNVERIFIED", "blocks": True},
    {"id": "CHAOS-002", "title": "decimal comma", "defect": "emissions value '1,9' (comma decimal) parsed as 19",
     "evidence_state": "UNVERIFIED", "blocks": True},
    {"id": "CHAOS-003", "title": "units embedded in cells", "defect": "cell contains '1.9 tCO2e/t' instead of numeric 1.9",
     "evidence_state": "UNVERIFIED", "blocks": True},
    {"id": "CHAOS-004", "title": "kg-tonne error", "defect": "1925 kgCO2e/t recorded as 1925 tCO2e/t (x1000)",
     "evidence_state": "UNVERIFIED", "blocks": True},
    {"id": "CHAOS-005", "title": "8-digit CN vs 10-digit TARIC", "defect": "8-digit CN supplied where 10-digit TARIC required",
     "evidence_state": "MISSING", "blocks": True},
    {"id": "CHAOS-006", "title": "stale Excel cached formula", "defect": "unsaved formula; cached value older than freshness policy",
     "evidence_state": "STALE", "blocks": True},
    {"id": "CHAOS-007", "title": "duplicate supplier", "defect": "same legal entity twice with different supplier_ids",
     "evidence_state": "CONFLICTING", "blocks": True},
    {"id": "CHAOS-008", "title": "conflicting installation IDs", "defect": "two active installation IDs for one supplier/facility",
     "evidence_state": "CONFLICTING", "blocks": True},
    {"id": "CHAOS-009", "title": "missing precursor", "defect": "precursor emissions section absent",
     "evidence_state": "MISSING", "blocks": True},
    {"id": "CHAOS-010", "title": "wrong reporting period", "defect": "data period outside declarant reporting quarter",
     "evidence_state": "EXPIRED", "blocks": True},
    {"id": "CHAOS-011", "title": "expired verification", "defect": "verifier statement past valid_to",
     "evidence_state": "EXPIRED", "blocks": True},
    {"id": "CHAOS-012", "title": "superseded certificate", "defect": "MTC superseded by re-issue, no active replacement linked",
     "evidence_state": "SUPERSEDED", "blocks": True},
    {"id": "CHAOS-013", "title": "duplicate invoice", "defect": "same invoice number posted twice for different lines",
     "evidence_state": "CONFLICTING", "blocks": True},
    {"id": "CHAOS-014", "title": "invoice/PO quantity mismatch", "defect": "invoiced quantity != PO quantity beyond tolerance",
     "evidence_state": "CONFLICTING", "blocks": True},
    {"id": "CHAOS-015", "title": "MTC heat number mismatch", "defect": "heat number on MTC != heat on packing list/invoice",
     "evidence_state": "CONFLICTING", "blocks": True},
]


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def write_json(p: Path, o) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(o, indent=2, sort_keys=True) + "\n")


def write_csv(p: Path, rows: list[dict]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def load_base() -> tuple[list[dict], list[dict], list[dict], dict]:
    tx = list(csv.DictReader((BASE / "evidence_room/transactions.csv").open()))
    suppliers = list(csv.DictReader((BASE / "evidence_room/suppliers.csv").open()))
    evidence = json.loads((BASE / "evidence_room/evidence.json").read_text())
    truth = json.loads((BASE / "evidence_room/fault_truth.json").read_text())
    return tx, suppliers, evidence, truth


def build(n_tx: int = 0, ems_rows: int = 2000) -> dict:
    rng = random.Random(SEED)
    tx_all, suppliers, evidence, truth = load_base()
    tx = tx_all[: n_tx] if n_tx else tx_all
    blocked_ids = set(truth["blocked_transactions"]) & {t["transaction_id"] for t in tx}

    # ---- ERP ----
    sales = [{"sales_order": f"SO-EU-{1000 + i}", "po_number": t["po_number"],
              "transaction_id": t["transaction_id"], "customer_country": t["destination"],
              "line_value_eur": t["line_value_eur"]} for i, t in enumerate(tx)]
    pos = [{"po_number": t["po_number"], "transaction_id": t["transaction_id"],
            "supplier_id": t["supplier_id"], "cn_code": t["cn_code"],
            "quantity_t": t["quantity_t"], "shipment_date": t["shipment_date"]} for t in tx]
    write_csv(ROOM / "ERP/sales_orders.csv", sales)
    write_csv(ROOM / "ERP/purchase_orders.csv", pos)
    write_csv(ROOM / "ERP/suppliers.csv", suppliers)

    # ---- LOGISTICS / QUALITY / CARBON manifests (one row per txn, no 1000s of PDFs) ----
    for folder, typ in [("LOGISTICS/invoices", "COMMERCIAL_INVOICE"),
                        ("LOGISTICS/packing_lists", "PACKING_LIST"),
                        ("LOGISTICS/customs_declarations", "TARIC_SUPPORTING_DOCUMENT"),
                        ("QUALITY/mill_test_certificates", "MILL_TEST_CERTIFICATE"),
                        ("CARBON/cbam_supplier_templates", "CBAM_INSTALLATION_DATA"),
                        ("CARBON/epds", "EPD"),
                        ("CARBON/verification", "VERIFICATION_STATEMENT")]:
        rows = [{"document_ref": f"{typ}-{t['transaction_id']}", "transaction_id": t["transaction_id"],
                 "present": str(any(e["transaction_id"] == t["transaction_id"] and e["type"] == typ
                                    for e in evidence) or typ in ("EPD", "VERIFICATION_STATEMENT")),
                 "heat_number": f"HEAT-{abs(hash(t['transaction_id'])) % 9000 + 1000}",
                 "sha256": sha(f"{typ}|{t['transaction_id']}".encode())} for t in tx]
        write_csv(ROOM / f"{folder}/manifest.csv", rows)

    # ---- CARBON telemetry (UCI-shaped: kWh, reactive power, CO2, load; deterministic) ----
    ems = [{"timestamp": f"2026-07-{(i % 28) + 1:02d}T{(i % 24):02d}:00:00",
            "facility_id": f"FAC-{(i % 25) + 1:02d}",
            "energy_kwh": round(rng.uniform(800, 5200), 2),
            "reactive_kvarh": round(rng.uniform(50, 900), 2),
            "co2_t": round(rng.uniform(0.4, 4.2), 4),
            "load_type": rng.choice(["Light_Load", "Medium_Load", "Maximum_Load"])} for i in range(ems_rows)]
    write_csv(ROOM / "CARBON/energy_meter.csv", ems)
    fac = [{"facility_id": f"FAC-{i:02d}", "route": "BF-BOF" if i % 3 else "EAF",
            "default_intensity_tco2e_per_t": 1.73 if i % 3 else 0.38,
            "source": "EC CBAM defaults/benchmarks (Layer-1 golden reference)"} for i in range(1, 26)]
    write_csv(ROOM / "CARBON/facility_emissions.csv", fac)

    # ---- REGULATORY snapshots (versioned pointers, not live data) ----
    for name, payload in [
        ("taric/snapshot.json", {"source": "EU TARIC (Layer-1)", "as_of": "2026-08-28",
                                 "note": "CN to measures/restrictions/documents; refresh via source_sync"}),
        ("cbam/snapshot.json", {"source": "EC CBAM defaults+benchmarks (Layer-1)",
                                "bf_bof_default": 1.73, "eaf_default": 0.38,
                                "note": "Only direct authoritative expected outputs are normative oracles"}),
        ("sanctions/snapshot.json", {"source": "EU sanctions map (Layer-1)", "as_of": "2026-08-28"})]:
        write_json(ROOM / f"REGULATORY/{name}", payload)

    # ---- corrupted derivatives (clean parent -> CHAOS variant, hash-linked) ----
    derivs = []
    for i, t in enumerate(tx):
        if t["transaction_id"] not in blocked_ids:
            continue
        chaos = CHAOS[i % len(CHAOS)]
        parent = sha(f"COMMERCIAL_INVOICE|{t['transaction_id']}".encode())
        derivs.append({"derivative_id": f"{t['transaction_id']}-{chaos['id']}",
                       "transaction_id": t["transaction_id"], "chaos_id": chaos["id"],
                       "title": chaos["title"], "defect": chaos["defect"],
                       "parent_artifact_sha256": parent,
                       "synthetic_transform": f"clean invoice manifest row -> {chaos['id']} ({chaos['title']})",
                       "expected_evidence_state": chaos["evidence_state"],
                       "expected_decision": "BLOCKED"})
    write_json(ROOM / "corrupted_derivatives.json", derivs)

    # ---- expected decisions (initial BLOCKED set -> remediation -> READY) ----
    blocked_value = round(sum(float(t["line_value_eur"]) for t in tx if t["transaction_id"] in blocked_ids), 2)
    total_value = round(sum(float(t["line_value_eur"]) for t in tx), 2)
    write_json(ROOM / "expected/initial_decisions.json",
               {"READY": len(tx) - len(blocked_ids), "BLOCKED": len(blocked_ids),
                "blocked_transactions": sorted(blocked_ids),
                "blocked_value_eur": blocked_value, "total_value_eur": total_value})
    write_json(ROOM / "expected/remediation_actions.json",
               [{"transaction_id": tid, "action": "ingest corrected evidence; recompile; link predecessor",
                 "chaos": next((d["chaos_id"] for d in derivs if d["transaction_id"] == tid), "BASE-FAULT")}
                for tid in sorted(blocked_ids)])
    write_json(ROOM / "expected/final_decisions.json",
               {"READY": len(tx), "BLOCKED": 0})

    # ---- provenance (every artifact, full trail) ----
    reg = {s["id"]: s for s in json.loads(CFG.read_text())["sources"]}
    prov = []
    for p in sorted(ROOM.rglob("*")):
        if not p.is_file() or p.name == "provenance.json":
            continue
        rel = str(p.relative_to(ROOT))
        prov.append({"path": rel, "sha256": sha(p.read_bytes()), "bytes": p.stat().st_size,
                     "source_type": "SYNTHETIC", "source_url": "",
                     "license": "synthetic demo data; no reuse restriction",
                     "retrieved_at": datetime.now(timezone.utc).isoformat(),
                     "original_filename": p.name, "synthetic_transform": "deterministic generator seed 20261002",
                     "parent_artifact": next((d["parent_artifact_sha256"] for d in derivs
                                              if d["derivative_id"] in rel), ""),
                     "expected_use": "Layer-4 ingestion/error-handling benchmark; not a normative oracle",
                     "registry_refs": ["cbamreturn_worked_example", "carbonchain_steelforce",
                                       "uci_steel_energy", "ec_cbam_examples"]})
    prov.append({"path": "config/public_evidence_sources.json",
                 "source_type": "REGISTRY", "source_url": "",
                 "license": "registry of Layer-1/2/3 pointers; see per-source license",
                 "retrieved_at": datetime.now(timezone.utc).isoformat(),
                 "sha256": sha(CFG.read_bytes()), "original_filename": "public_evidence_sources.json",
                 "synthetic_transform": "", "parent_artifact": "",
                 "expected_use": "Layer-1/2/3 source manifest; landing pages/APIs never scraped",
                 "registry_refs": sorted(reg.keys())})
    write_json(ROOM / "provenance.json", {"generated_at": datetime.now(timezone.utc).isoformat(),
                                          "layers": ["regulatory-goldens", "public-real-world",
                                                     "competitor-scenarios", "synthetic-corrupted"],
                                          "artifacts": prov})
    return {"transactions": len(tx), "blocked": len(blocked_ids),
            "derivatives": len(derivs), "ems_rows": len(ems), "provenance_entries": len(prov)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clean", action="store_true")
    ap.add_argument("--transactions", type=int, default=0)
    ap.add_argument("--ems-rows", type=int, default=2000)
    a = ap.parse_args()
    if a.clean and ROOM.exists():
        import shutil
        shutil.rmtree(ROOM)
    if not (BASE / "evidence_room/transactions.csv").exists():
        raise SystemExit("base corpus missing: run scripts/build_public_evidence_corpus.py --clean first")
    print(json.dumps({"room": str(ROOM.relative_to(ROOT)), **build(a.transactions, a.ems_rows)}, indent=2))


if __name__ == "__main__":
    main()
