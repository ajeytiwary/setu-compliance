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


def load_uci_telemetry(max_rows: int) -> tuple[list[dict], dict]:
    """Load real UCI Steel Industry Energy Consumption telemetry if acquired.

    Returns (rows, meta). Falls back to ([], {source: synthetic}) when the
    acquired zip is absent (offline deterministic path). Real rows map:
      date -> timestamp (ISO), Usage_kWh -> energy_kwh,
      Lagging+Leading kVarh -> reactive_kvarh, CO2(tCO2) -> co2_t,
      Load_Type -> load_type. facility_id round-robins FAC-01..25 so the
      telemetry -> facility -> installation -> product -> shipment chain
      stays joinable. CC BY 4.0 — attribution kept in meta + provenance.
    """
    import zipfile
    meta: dict = {"source": "synthetic fallback (seed 20261002)",
                  "source_type": "SYNTHETIC", "real_rows": 0}
    zips = sorted((BASE / "originals/uci_steel_energy_zip").glob("*.zip"))
    if not zips:
        return [], meta
    zpath = zips[0]
    with zipfile.ZipFile(zpath) as z:
        raw = z.read("Steel_industry_data.csv").decode("utf-8-sig")
    reader = csv.DictReader(raw.splitlines())
    rows: list[dict] = []
    for i, r in enumerate(reader):
        if i >= max_rows:
            break
        # date format "01/01/2018 00:15" -> "2018-01-01T00:15:00"
        day, rest = r["date"].split(" ", 1)
        dd, mm, yyyy = day.split("/")
        rows.append({
            "timestamp": f"{yyyy}-{mm}-{dd}T{rest}:00",
            "facility_id": f"FAC-{(i % 25) + 1:02d}",
            "energy_kwh": float(r["Usage_kWh"]),
            "reactive_kvarh": round(float(r["Lagging_Current_Reactive.Power_kVarh"])
                                    + float(r["Leading_Current_Reactive_Power_kVarh"]), 2),
            "co2_t": float(r["CO2(tCO2)"]),
            "load_type": r["Load_Type"],
            "source_row": i + 1,
        })
    meta = {"source": "UCI Steel Industry Energy Consumption — DAEWOO Steel Gwangyang (CC BY 4.0, DOI 10.24432/C52G8C)",
            "source_type": "ACADEMIC_OPEN_DATA",
            "source_url": "https://archive.ics.uci.edu/static/public/851/steel+industry+energy+consumption.zip",
            "license": "CC BY 4.0 (attribute Sathishkumar V E, Shin, Cho 2021)",
            "original_filename": "Steel_industry_data.csv",
            "parent_artifact_sha256": sha(zpath.read_bytes()),
            "real_rows": len(rows),
            "columns": ["date", "Usage_kWh", "Lagging_Current_Reactive.Power_kVarh",
                        "Leading_Current_Reactive_Power_kVarh", "CO2(tCO2)",
                        "Lagging_Current_Power_Factor", "Leading_Current_Power_Factor",
                        "NSM", "WeekStatus", "Day_of_week", "Load_Type"]}
    return rows, meta


def write_terlouw_research_summary() -> dict:
    """Materialize the Terlouw Steel_CBAM research-corpus pointer (Layer-2).

    Never a normative oracle: records the Zenodo record structure, license,
    and expected research use so telemetry -> LCA-prior linkage is traceable.
    Returns the summary dict (also written to CARBON/research/)."""
    import zipfile
    zips = sorted((BASE / "originals/terlouw_steel_cbam_zenodo").glob("*.zip"))
    summary: dict = {
        "record": "Terlouw, Harpprecht & Bauer (2025) — Steel_CBAM",
        "doi_data": "10.5281/zenodo.17236022",
        "doi_paper": "10.1016/j.jclepro.2025.145000",
        "license": "BSD-3-Clause (code+data); paper via publisher",
        "repo_layout": ["steel_cbam_assessment/data/", "figs/", "logs/", "results/",
                        "notebooks 0-5", "config.py", "db_functions.py", "functions.py",
                        "mapping.py", "plotting.py", "regionalization.py"],
        "expected_use": ("Layer-2 research corpus: regionalized steel production + "
                         "prospective LCA inputs as installation intensity priors. "
                         "Research only — never a normative calculation oracle."),
        "chain": "plant telemetry (UCI) -> emissions evidence -> CBAM installation workbook -> product -> shipment; Terlouw provides regional/LCA priors",
    }
    if zips:
        zpath = zips[0]
        with zipfile.ZipFile(zpath) as z:
            names = sorted(z.namelist())
            try:
                readme = z.read("tomterlouw-Steel_CBAM-cfab341/README.md").decode("utf-8", "replace")
            except KeyError:
                readme = ""
        summary.update({
            "source_url": "https://zenodo.org/api/records/17236022/files/tomterlouw/Steel_CBAM-v.1.0.0.alpha.zip/content",
            "parent_artifact_sha256": sha(zpath.read_bytes()),
            "file_count": len(names),
            "readme_head": readme[:2000],
        })
    else:
        summary["note"] = "acquired zip absent — run build_public_evidence_corpus.py --acquire"
    write_json(ROOM / "CARBON/research/terlouw_steel_cbam_summary.json", summary)
    return summary


def write_sample_mtc(tx: list[dict]) -> dict:
    """Write a synthetic EN 10204 3.1-shaped sample MTC (Layer-4).

    Shape inspired by public plate mill certificates (e.g. 200 pieces /
    ~542 t heat lots); all values synthetic, linked to room heat numbers.
    The Scribd example is shape reference only — never copied/redistributed."""
    rng = random.Random(SEED + 7)
    grades = ["S355J2+N", "S355JR", "P355GH", "S690QL", "DX51D+Z"]
    rows = []
    for i, t in enumerate(tx[:10]):
        heat = f"HEAT-{abs(hash(t['transaction_id'])) % 9000 + 1000}"
        pieces = rng.choice([120, 200, 240])
        tonnes = round(pieces * rng.uniform(2.4, 2.9), 3)
        rows.append({
            "certificate_no": f"MTC-2026-{1000 + i}",
            "transaction_id": t["transaction_id"],
            "heat_number": heat,
            "standard": "EN 10204 3.1",
            "grade": grades[i % len(grades)],
            "dimensions_mm": f"{rng.choice([8, 10, 12, 16, 20])}x{rng.choice([1500, 2000, 2500])}x{rng.choice([6000, 12000])}",
            "pieces": pieces,
            "quantity_t": tonnes,
            "c_pct": round(rng.uniform(0.12, 0.20), 3),
            "mn_pct": round(rng.uniform(1.1, 1.6), 2),
            "yield_mpa": rng.choice([355, 360, 372, 690]),
            "tensile_mpa": rng.choice([490, 510, 530, 770]),
            "inspector": "synthetic",
        })
    write_csv(ROOM / "QUALITY/mill_test_certificates/sample_mtc_en10204_31.csv", rows)
    write_json(ROOM / "QUALITY/mill_test_certificates/shape_note.json", {
        "note": ("Synthetic EN 10204 3.1-shaped sample. Public plate certificates "
                 "(e.g. 200-piece / ~542 t lots) used as shape reference only; "
                 "no third-party document copied or redistributed."),
        "linked_manifest": "QUALITY/mill_test_certificates/manifest.csv",
    })
    return {"sample_mtc_rows": len(rows)}


def write_epd_pointer() -> dict:
    """Write the voestalpine EPD pointer (link + expected use, no PDF copied)."""
    pointer = {
        "source": "voestalpine steel EPDs (heavy plate, hot-rolled, cold-rolled strip)",
        "source_url": "https://www.voestalpine.com/group/en/group/environment/environmental-product-declarations/",
        "license": "public PDFs; verify reuse before acquisition — link only, never redistributed",
        "expected_use": ("Layer-2 real-world: EPD/PCF evidence-document inputs linked "
                         "to heat/batch/facility; see CARBON/epds/manifest.csv"),
        "linked_manifest": "CARBON/epds/manifest.csv",
    }
    write_json(ROOM / "CARBON/epds/epd_sources.json", pointer)
    return pointer


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

    # ---- CARBON telemetry (real UCI rows when acquired; synthetic fallback) ----
    real_ems, ems_meta = load_uci_telemetry(ems_rows)
    if real_ems:
        ems = real_ems
        ems_source = ems_meta["source"]
    else:
        ems = [{"timestamp": f"2026-07-{(i % 28) + 1:02d}T{(i % 24):02d}:00:00",
                "facility_id": f"FAC-{(i % 25) + 1:02d}",
                "energy_kwh": round(rng.uniform(800, 5200), 2),
                "reactive_kvarh": round(rng.uniform(50, 900), 2),
                "co2_t": round(rng.uniform(0.4, 4.2), 4),
                "load_type": rng.choice(["Light_Load", "Medium_Load", "Maximum_Load"])} for i in range(ems_rows)]
        ems_source = "synthetic fallback (seed 20261002)"
    write_csv(ROOM / "CARBON/energy_meter.csv", ems)
    write_json(ROOM / "CARBON/energy_meter_meta.json", {**ems_meta, "rows": len(ems),
               "chain": "plant telemetry -> emissions evidence -> CBAM installation workbook -> product -> shipment"})
    fac = [{"facility_id": f"FAC-{i:02d}", "route": "BF-BOF" if i % 3 else "EAF",
            "default_intensity_tco2e_per_t": 1.73 if i % 3 else 0.38,
            "source": "EC CBAM defaults/benchmarks (Layer-1 golden reference)"} for i in range(1, 26)]
    write_csv(ROOM / "CARBON/facility_emissions.csv", fac)
    terlouw = write_terlouw_research_summary()
    mtc = write_sample_mtc(tx)
    epd = write_epd_pointer()

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
        entry = {"path": rel, "sha256": sha(p.read_bytes()), "bytes": p.stat().st_size,
                     "source_type": "SYNTHETIC", "source_url": "",
                     "license": "synthetic demo data; no reuse restriction",
                     "retrieved_at": datetime.now(timezone.utc).isoformat(),
                     "original_filename": p.name, "synthetic_transform": "deterministic generator seed 20261002",
                     "parent_artifact": next((d["parent_artifact_sha256"] for d in derivs
                                              if d["derivative_id"] in rel), ""),
                     "expected_use": "Layer-4 ingestion/error-handling benchmark; not a normative oracle",
                     "registry_refs": ["cbamreturn_worked_example", "carbonchain_steelforce",
                                       "uci_steel_energy", "ec_cbam_examples"]}
        # Real-data overlays: correct source_type/license/parent for Layer-2 artifacts.
        if rel.endswith("CARBON/energy_meter.csv") and ems_meta.get("source_type") == "ACADEMIC_OPEN_DATA":
            entry.update({"source_type": "ACADEMIC_OPEN_DATA",
                          "source_url": ems_meta["source_url"], "license": ems_meta["license"],
                          "original_filename": ems_meta["original_filename"],
                          "synthetic_transform": f"column-mapped from acquired zip ({ems_meta['real_rows']} rows); facility_id round-robin FAC-01..25",
                          "parent_artifact": ems_meta["parent_artifact_sha256"],
                          "expected_use": "Layer-2 real-world: plant telemetry -> emissions evidence -> CBAM installation workbook -> product -> shipment",
                          "registry_refs": ["uci_steel_energy", "uci_steel_energy_zip"]})
        if rel.endswith("CARBON/energy_meter_meta.json") and ems_meta.get("source_type") == "ACADEMIC_OPEN_DATA":
            entry.update({"source_type": "ACADEMIC_OPEN_DATA",
                          "source_url": ems_meta["source_url"], "license": ems_meta["license"],
                          "synthetic_transform": "column-mapping record for UCI telemetry",
                          "parent_artifact": ems_meta["parent_artifact_sha256"],
                          "expected_use": "Layer-2 provenance for energy_meter.csv; CC BY 4.0 attribution",
                          "registry_refs": ["uci_steel_energy", "uci_steel_energy_zip"]})
        if rel.endswith("CARBON/research/terlouw_steel_cbam_summary.json") and terlouw.get("parent_artifact_sha256"):
            entry.update({"source_type": "ACADEMIC_OPEN_DATA",
                          "source_url": terlouw["source_url"], "license": terlouw["license"],
                          "original_filename": "tomterlouw/Steel_CBAM-v.1.0.0.alpha.zip",
                          "synthetic_transform": "research-corpus pointer; repo structure + README head extracted, no code executed",
                          "parent_artifact": terlouw["parent_artifact_sha256"],
                          "expected_use": terlouw["expected_use"],
                          "registry_refs": ["terlouw_steel_cbam", "terlouw_steel_cbam_zenodo"]})
        if rel.endswith("CARBON/epds/epd_sources.json"):
            entry.update({"source_type": "PUBLIC_COMPANY", "source_url": epd["source_url"],
                          "license": "public PDFs; link only, never redistributed",
                          "synthetic_transform": "link pointer only; no PDF copied",
                          "expected_use": epd["expected_use"],
                          "registry_refs": ["voestalpine_epds"]})
        if rel.endswith("QUALITY/mill_test_certificates/sample_mtc_en10204_31.csv"):
            entry.update({"synthetic_transform": "synthetic EN 10204 3.1-shaped rows linked to room heat numbers (seed 20261002+7); public plate certs used as shape reference only",
                          "expected_use": "Layer-4 evidence-document input: MTC heat/batch linkage; not a normative oracle"})
        prov.append(entry)
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
            "derivatives": len(derivs), "ems_rows": len(ems), "ems_source": ems_source,
            "ems_real_rows": ems_meta.get("real_rows", 0),
            "terlouw_files": terlouw.get("file_count", 0), **mtc,
            "provenance_entries": len(prov)}


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
