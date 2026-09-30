"""Load the JSW Vijayanagar HRC demo portfolio into the local demo DB.

Usage (from repo root):
    PYTHONPATH=. .venv/bin/python scripts/load_jsw_demo.py
    PYTHONPATH=. .venv/bin/python scripts/load_jsw_demo.py --reset

What it does (all synthetic commercial rows, public regulatory context):
 1. init_db + import all 14 connector samples (ERP/MES/EMS backbone)
 2. inject JSW-specific canonical rows (SAP SD / MES genealogy / EMS activity /
    supplier CBAM / verifier) so POST /api/pipeline/steel/{ref}/cbam works
 3. create 8 shipments from examples/jsw_vijayanagar_demo_portfolio.json
 4. create demo suppliers, link them, add VERIFIED precursor evidence for the
    hero + precursor shipments (verify-once/share-many loop)

Honesty: commercial rows are SYNTHETIC. Regulatory tables come from configured
source snapshots. No JSW private systems are touched. See
docs/PUBLIC_CASE_STUDY.md and docs/JSW_VIJAYANAGAR_DEMO.md.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.db import connect, init_db  # noqa: E402
from app.integrations import import_csv, import_sample, integration_catalog  # noqa: E402
from app.rules import STEEL_EU_RULES, initial_status  # noqa: E402
from app.evidence_network import (  # noqa: E402
    create_supplier,
    link_supplier,
    add_supplier_evidence,
)

PORTFOLIO = ROOT / "examples" / "jsw_vijayanagar_demo_portfolio.json"
EXPORTER = "JSW Steel Limited (demo — synthetic commercial rows)"
FACILITY = "Vijayanagar Works, Karnataka, India"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_backbone() -> None:
    for c in integration_catalog()["connectors"]:
        try:
            import_sample(c["code"])
        except Exception as e:  # noqa: BLE001 — demo loader must keep going
            print(f"warn: sample {c['code']} failed: {e}")


def inject_canonical(s) -> None:
    """Inject per-shipment SAP SD / MES / EMS rows so the steel pipeline assembles."""
    ref = s["shipment_ref"]
    batch = s.get("batch_id", f"BATCH-{ref}")
    qty = float(s["quantity_t"])
    val = float(s["customs_value_eur"])
    dest = s["destination_country"]
    cn = s["cn_code"]
    heat = f"HEAT-{ref}"
    slab = f"SLAB-{ref}"

    sap_csv = (
        "shipment_id,sales_order,delivery_id,invoice_id,invoice_date,customer_id,"
        "destination_country,material_id,batch_id,quantity_t,invoice_value_eur,currency,cn_code\n"
        f"{ref},SO-{ref},DEL-{ref},INV-{ref},2026-08-20,CUST-{dest}-JSW,"
        f"{dest},{s.get('product','Hot Rolled Coil').replace(' ','-').upper()},{batch},"
        f"{qty},{val},EUR,{cn}\n"
    )
    import_csv("sap_sd", sap_csv, source_name="jsw-demo")

    mes_csv = (
        "event_time,plant,process,parent_type,parent_id,child_type,child_id,quantity_t,production_line\n"
        f"2026-08-18T08:00:00,Vijayanagar,BOF,HEAT,{heat},SLAB,{slab},{qty + 200},BOF-1\n"
        f"2026-08-18T14:00:00,Vijayanagar,HSM,SLAB,{slab},COIL,{batch},{qty},HSM-2\n"
    )
    # PL-008 genealogy scenario: skip MES injection so the blocker is real
    if s.get("demo_scenario") != "GENEALOGY":
        import_csv("mes", mes_csv, source_name="jsw-demo")

    ems_csv = (
        "timestamp,installation,production_process,source_id,activity_type,quantity,unit,"
        "measurement_method,quality_flag,measured_emissions_tco2,"
        "emission_factor_tco2_per_unit,oxidation_factor,conversion_factor\n"
        f"2026-08-18T08:00:00,Vijayanagar,Integrated-HRC,SRC-BF-BOF-{ref},"
        f"process_and_combustion,{qty},t,METERED_AND_MASS_BALANCE,VALID,"
        f"{round(qty * 1.55, 1)},,,,1\n"
    )
    import_csv("ems_activity", ems_csv, source_name="jsw-demo")


def inject_supplier_verifier() -> dict:
    sup_csv = (
        "supplier_id,installation_id,precursor_cn,precursor_name,period_start,period_end,"
        "specific_embedded_emissions,unit,verification_status,evidence_ref,quantity_t\n"
        "SUP-JSW-FE-01,SUPPLIER-INSTALLATION-FE-01,72021100,Ferromanganese,"
        "2026-01-01,2026-06-30,1.8,tCO2e/t,VERIFIED,CBAM-SUP-JSW-FE-001,250\n"
    )
    import_csv("supplier_cbam", sup_csv, source_name="jsw-demo")
    # Verifier record scoped to the hero shipment only: NL-001 resolves
    # CALCULATED_VERIFIED while DE-002 (same installation, no verifier row)
    # resolves CALCULATED_UNVERIFIED — the demo's verification contrast.
    ver_csv = (
        "shipment_id,installation_id,reporting_period,verifier,accreditation_ref,status,"
        "started_at,completed_at,findings,statement_ref\n"
        "JSW-HRC-NL-001,VIJAYANAGAR-HRC-01 (demo),2026-H1,Demo Verifier EU,ACC-DEMO-001,VERIFIED,"
        "2026-07-01,2026-07-05,0,VER-STMT-JSW-001\n"
    )
    import_csv("verifier", ver_csv, source_name="jsw-demo")
    return {"supplier_id": "SUP-JSW-FE-01"}


def create_shipments(items) -> list:
    created = []
    with connect() as conn:
        for s in items:
            ref = s["shipment_ref"]
            existing = conn.execute(
                "SELECT id FROM shipments WHERE shipment_no=?", (ref,)
            ).fetchone()
            if existing:
                created.append({"shipment_no": ref, "id": existing[0], "skipped": True})
                continue
            sid = str(uuid4())
            now = _now()
            # Hero carries an actual intensity so CBAM_EMISSIONS starts PASS;
            # the rest start MISSING to show the blocker honestly.
            embedded = 1.73 if ref == "JSW-HRC-NL-001" else None
            row = {
                "shipment_no": ref,
                "exporter": EXPORTER,
                "facility": FACILITY,
                "importer": f"Demo EU importer {s['destination_country']} ({s.get('destination_port','')})",
                "destination_country": s["destination_country"],
                "product": s.get("product", "Hot Rolled Coil"),
                "cn_code": s["cn_code"],
                "tonnes": float(s["quantity_t"]),
                "value_eur": float(s["customs_value_eur"]),
                "emissions_method": "actual",
                "embedded_emissions_tco2e_per_t": embedded,
                "supplier_required": 2,
                "supplier_complete": 0,
                "manual_hours": 6.0,
            }
            conn.execute(
                "INSERT INTO shipments(id,shipment_no,exporter,facility,importer,"
                "destination_country,product,cn_code,tonnes,value_eur,emissions_method,"
                "embedded_emissions_tco2e_per_t,supplier_required,supplier_complete,"
                "manual_hours,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (sid, row["shipment_no"], row["exporter"], row["facility"], row["importer"],
                 row["destination_country"], row["product"], row["cn_code"], row["tonnes"],
                 row["value_eur"], row["emissions_method"], row["embedded_emissions_tco2e_per_t"],
                 row["supplier_required"], row["supplier_complete"], row["manual_hours"], now, now),
            )
            for r in STEEL_EU_RULES:
                conn.execute(
                    "INSERT INTO requirements(shipment_id,code,label,category,blocking,"
                    "status,required_evidence,evidence_count) VALUES(?,?,?,?,?,?,?,0)",
                    (sid, r.code, r.label, r.category, int(r.blocking),
                     initial_status(r, row), r.required_evidence),
                )
            created.append({"shipment_no": ref, "id": sid, "skipped": False})
    return created


def wire_suppliers(created) -> None:
    ids = {c["shipment_no"]: c["id"] for c in created}
    from app.evidence_network import get_supplier  # noqa: E402

    sup_id = "SUP-JSW-FE-01-DEMO"
    fe = get_supplier(sup_id)
    if not fe:
        fe = create_supplier(
            name="Demo Ferroalloys (JSW demo)",
            facility="Vijayanagar supplier park (demo)",
            country="IN",
            supplier_id=sup_id,
        )
    sup_id = fe["id"]
    for ref, material in (
        ("JSW-HRC-NL-001", "Ferromanganese"),
        ("JSW-HRC-FR-006", "Ferromanganese"),
    ):
        if ref in ids:
            try:
                link_supplier(sup_id, ids[ref], material=material,
                              quantity_t=250.0, required_evidence_type="CBAM_PRECURSOR")
            except ValueError:
                pass
    ev = add_supplier_evidence(
        sup_id, evidence_type="CBAM_PRECURSOR",
        content="demo verified precursor EPD + installation emissions annexe",
        status="VERIFIED", issuer="Demo Ferroalloys", verifier="Demo Verifier EU",
        source_ref="CBAM-SUP-JSW-FE-001",
        metadata={"precursor_cn": "72021100", "specific_embedded_emissions": 1.8},
    )
    print(f"supplier {sup_id} VERIFIED evidence {ev['id']}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true",
                    help="delete JSW-HRC demo shipments first (demo DB only)")
    args = ap.parse_args()

    init_db()
    if args.reset:
        with connect() as conn:
            conn.execute("DELETE FROM shipments WHERE shipment_no LIKE 'JSW-%'")
            # Clear demo canonical records so re-runs are idempotent: the
            # pipeline assembles from canonical_records, and stale verifier /
            # activity rows would otherwise mask the demo's intended contrast
            # (NL-001 VERIFIED vs DE-002 UNVERIFIED).
            conn.execute("DELETE FROM canonical_records WHERE source_key LIKE 'JSW-%' OR source_key LIKE 'SO-JSW-%' OR source_key LIKE 'BATCH-JSW-%'")
            conn.execute("DELETE FROM canonical_records WHERE connector='verifier' AND (payload_json LIKE '%JSW-HRC-NL-001%' OR payload_json LIKE '%VIJAYANAGAR-HRC-01 (demo)%')")
        print("reset: JSW-% shipments + demo canonical records removed")

    ensure_backbone()
    data = json.loads(PORTFOLIO.read_text())
    for s in data["shipments"]:
        inject_canonical(s)
    inject_supplier_verifier()
    created = create_shipments(data["shipments"])
    wire_suppliers(created)
    total = sum(s["customs_value_eur"] for s in data["shipments"])
    print(f"JSW demo loaded: {len(created)} shipments, "
          f"EUR {total:,.0f} bound ({data['provenance']})")
    for c in created:
        print(f"  {'SKIP' if c.get('skipped') else 'NEW '} {c['shipment_no']}")


if __name__ == "__main__":
    main()
