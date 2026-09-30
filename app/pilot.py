from __future__ import annotations
"""Pilot operations dashboard backend.

Separate from the customer-facing website (``/``) and the public demo
(``/demo``). ``/pilot`` is the working view for a live pilot team
(internal operators plus the pilot customer) tracking the 12-week plan
(``docs/12_WEEK_PLAN.md``), the six pilot data contracts
(``docs/PILOT_DATA_CONTRACT.md``), shipment readiness, CBAM
reproducibility, remediation and regulatory-snapshot provenance.

Everything here is read-only aggregation over existing stores. Statuses
are system signals (row counts, manifests), never certifications.
"""
from .db import connect, rows

PILOT_WEEKS = [
    {"week": 1, "objective": "Pilot boundary, security and data contracts",
     "exit": "10–30 representative EU shipments selected; owners and access approved",
     "signal": "shipments"},
    {"week": 2, "objective": "Live SAP SD/FI",
     "exit": "≥95% invoice-value reconciliation for selected shipments",
     "signal": "sap_rows"},
    {"week": 3, "objective": "SAP MM/PP + MES genealogy",
     "exit": "≥95% shipped-tonnage genealogy coverage heat→slab→coil→shipment",
     "signal": "genealogy_edges"},
    {"week": 4, "objective": "EMS/SCADA + LIMS",
     "exit": "Meter/activity and quality evidence mapped to production process",
     "signal": "activity_rows"},
    {"week": 5, "objective": "Supplier/precursor evidence",
     "exit": "Required precursor suppliers represented with evidence status",
     "signal": "supplier_evidence_rows"},
    {"week": 6, "objective": "CBAM calculation engine",
     "exit": "Results reconciled against compliance workbook; versioned + reproducible",
     "signal": "cbam_calculations"},
    {"week": 7, "objective": "Verifier workflow",
     "exit": "Findings, evidence requests and verification status persisted",
     "signal": "verifier_rows"},
    {"week": 8, "objective": "TARIC/current MFN + customs",
     "exit": "Date/CN-specific customs treatment and required docs evaluated",
     "signal": "customs_snapshot"},
    {"week": 9, "objective": "EU–India origin readiness",
     "exit": "BOM/origin evaluable against authoritative PSRs; no premature FTA preference",
     "signal": "origin_evaluations"},
    {"week": 10, "objective": "ESPR/DPP outputs",
     "exit": "DPP/readiness output generated from same canonical facts",
     "signal": "manual"},
    {"week": 11, "objective": "Market-access economics",
     "exit": "Real € order book, ready value, revenue at risk, CBAM exposure, drilldown",
     "signal": "shipments"},
    {"week": 12, "objective": "Security, UAT and pilot sign-off",
     "exit": "RBAC, audit, backup/restore, tests and customer acceptance completed",
     "signal": "manual"},
]

DATA_CONTRACTS = [
    {"id": "sap_sd", "label": "SAP SD/FI: EU deliveries, invoices, CN code",
     "connectors": ["sap_sd"], "unlocks": "Value-weighted readiness metric"},
    {"id": "sap_mm", "label": "SAP MM: receipts, batches, suppliers, origin",
     "connectors": ["sap_mm"], "unlocks": "BOM + origin inputs"},
    {"id": "mes", "label": "MES: heat to slab to coil genealogy",
     "connectors": ["mes"], "unlocks": "Genealogy coverage"},
    {"id": "ems", "label": "EMS and historian: fuels, activity, metered observations",
     "connectors": ["ems_activity", "scada_ems"], "unlocks": "CBAM methodology inputs"},
    {"id": "supplier_cbam", "label": "Supplier CBAM feed: precursor emissions and evidence",
     "connectors": ["supplier_cbam"], "unlocks": "Precursor actuals vs defaults"},
    {"id": "verifier", "label": "Verifier feed: engagement, findings, statement",
     "connectors": ["verifier"], "unlocks": "CALCULATED_VERIFIED status"},
]

SCOPE_NOTICE = (
    "Pilot working view for the delivery team and the pilot customer. "
    "Commercial rows are pilot-supplied or synthetic demo data until the pilot "
    "data contract replaces them; regulatory context comes from versioned source "
    "snapshots. Terminal states are BLOCKED and READY_FOR_SUBMISSION, "
    "READY_FOR_SUBMISSION is engineering assurance, not customs acceptance, "
    "CBAM Registry acceptance, legal certification or verifier accreditation."
)


def _week_status(signal: str, value) -> str:
    if signal == "manual":
        return "MANUAL_TRACKING"
    if isinstance(value, bool):
        return "SIGNAL_PRESENT" if value else "NO_SIGNAL"
    return "SIGNAL_PRESENT" if (value or 0) > 0 else "NO_SIGNAL"


def pilot_overview() -> dict:
    from .risk_drilldown import risk_drilldown
    from .evidence_network import remediation_summary
    from .cbam_engine import list_calculations
    from .integrations import integration_catalog

    risk = risk_drilldown()
    remediation = remediation_summary()
    calculations = list_calculations()
    catalog = integration_catalog()
    last_run = {c["code"]: c.get("last_run") for c in catalog["connectors"]}
    required_cols = {c["code"]: c.get("required_columns", []) for c in catalog["connectors"]}

    with connect() as conn:
        shipments = rows(conn, """SELECT s.id, s.shipment_no, s.destination_country,
            s.product, s.cn_code, s.tonnes, s.value_eur,
            (SELECT COUNT(*) FROM requirements r WHERE r.shipment_id=s.id
             AND r.blocking=1 AND r.status!='PASS') AS open_blockers,
            (SELECT COUNT(*) FROM requirements r WHERE r.shipment_id=s.id
             AND r.blocking=1) AS blocking_total
            FROM shipments s ORDER BY s.value_eur DESC LIMIT 200""")
        first_blockers = rows(conn, """SELECT shipment_id, code, label FROM requirements
            WHERE blocking=1 AND status!='PASS' GROUP BY shipment_id HAVING MIN(code)""")
        canon_counts = {r["connector"]: r["c"] for r in rows(conn,
            "SELECT connector, COUNT(*) c FROM canonical_records GROUP BY connector")}
        genealogy_edges = conn.execute("SELECT COUNT(*) FROM genealogy_edges").fetchone()[0]
        activity_rows = conn.execute("SELECT COUNT(*) FROM activity_records").fetchone()[0]
        origin_evals = conn.execute("SELECT COUNT(*) FROM origin_evaluations").fetchone()[0]
        audit = rows(conn, """SELECT id, shipment_id, event_type, created_at FROM audit_events
            ORDER BY id DESC LIMIT 20""")

    fb = {r["shipment_id"]: {"code": r["code"], "label": r["label"]} for r in first_blockers}
    for s in shipments:
        s["ready"] = s["open_blockers"] == 0
        s["first_blocker"] = fb.get(s["id"])

    sap_rows = canon_counts.get("sap_sd", 0)
    verifier_rows = canon_counts.get("verifier", 0)

    try:
        from .data_sources import status as _ds_status
        from pathlib import Path as _Path
        import json as _json
        _ds = _ds_status()
        _norm_root = _Path(__file__).resolve().parents[1] / "data" / "normalized"
        regulatory = {}
        for _k, _v in _ds.items():
            _snap = _v.get("snapshot")
            _man_v, _man_sha = None, None
            try:
                from .source_resolvers import latest_manifest as _lm
                _man = _lm(_k)
                if _man:
                    _man_v, _man_sha = _man.get("version"), _man.get("sha256")
            except Exception:
                pass
            # Fallback: the AUTO pipeline (app/source_sync.py) writes
            # data/normalized/<ds>/latest.json + data/manifests/<ds>/<sha>.json
            # without a *-latest.json pointer, read those directly.
            if not _snap:
                _lp = _norm_root / _k / "latest.json"
                if _lp.exists():
                    try:
                        _lj = _json.loads(_lp.read_text())
                        _recs = _lj.get("records")
                        _snap = {
                            "provider": _lj.get("provider"),
                            "authority": _lj.get("authority"),
                            "legal_authority": _lj.get("legal_authority"),
                            "sha256": _lj.get("sha256"),
                            "record_count": (len(_recs) if isinstance(_recs, list)
                                             else _lj.get("validation", {}).get("record_count")),
                        }
                        _man_v = _man_v or _lj.get("sha256", "")[:12]
                        _man_sha = _man_sha or _lj.get("sha256")
                    except Exception:
                        pass
            regulatory[_k] = {
                "purpose": _v.get("purpose"),
                "refresh": _v.get("refresh"),
                "snapshot": _snap,
                "manifest_version": _man_v,
                "manifest_sha": _man_sha,
            }
        # steel_2026_1457 has no normalized pipeline yet; the checked-in
        # data/eu_steel_measure_2026.json is the working snapshot.
        _steel = _norm_root.parents[0] / "eu_steel_measure_2026.json"
        if _steel.exists() and not (regulatory.get("steel_2026_1457") or {}).get("snapshot"):
            try:
                _sj = _json.loads(_steel.read_text())
                _cats = _sj.get("categories", [])
                regulatory["steel_2026_1457"]["snapshot"] = {
                    "provider": "eu_steel_measure_2026_json",
                    "authority": "OFFICIAL",
                    "legal_authority": False,
                    "record_count": len(_cats) if isinstance(_cats, list) else 1,
                }
            except Exception:
                pass
        customs_snapshot = bool(
            (regulatory.get("steel_2026_1457") or {}).get("snapshot")
            or (regulatory.get("taric_measures") or {}).get("snapshot")
            or (regulatory.get("eucdm") or {}).get("snapshot")
        )
    except Exception as e:  # pilot dashboard must never fail on provenance
        regulatory = {"error": str(e)}
        customs_snapshot = False

    signals = {
        "shipments": len(shipments),
        "sap_rows": sap_rows,
        "genealogy_edges": genealogy_edges,
        "activity_rows": activity_rows,
        "supplier_evidence_rows": canon_counts.get("supplier_cbam", 0),
        "cbam_calculations": len(calculations),
        "verifier_rows": verifier_rows,
        "customs_snapshot": customs_snapshot,
        "origin_evaluations": origin_evals,
        "manual": None,
    }
    weeks = [{**w, "signal_value": signals[w["signal"]],
              "status": _week_status(w["signal"], signals[w["signal"]])}
             for w in PILOT_WEEKS]

    contracts = []
    for c in DATA_CONTRACTS:
        n = sum(canon_counts.get(x, 0) for x in c["connectors"])
        runs = [last_run.get(x) for x in c["connectors"] if last_run.get(x)]
        sample_only = bool(runs) and all(
            str(r.get("source_name", "")).startswith("sample:") for r in runs)
        contracts.append({
            **c,
            "rows": n,
            "status": "CONNECTED_ROWS" if n > 0 else "NO_ROWS",
            "sample_only": sample_only,
            "last_run": max((r.get("started_at", "") for r in runs), default=None),
            "required_columns": sorted({col for x in c["connectors"]
                                        for col in required_cols.get(x, [])}),
        })

    metrics = risk.get("metrics", {})
    kpis = {
        "shipments": len(shipments),
        "order_book_eur": metrics.get("eu_order_book_eur", 0),
        "ready_pct": metrics.get("market_ready_value_pct", 0),
        "revenue_at_risk_eur": metrics.get("revenue_at_risk_eur", 0),
        "cbam_calculations": len(calculations),
        "cbam_verified": sum(1 for c in calculations if c.get("status") == "CALCULATED_VERIFIED"),
        "open_requests": remediation.get("open_requests", 0),
        "genealogy_edges": genealogy_edges,
        "activity_rows": activity_rows,
    }
    return {
        "scope": {"audience": "pilot delivery team + pilot customer", "notice": SCOPE_NOTICE},
        "kpis": kpis,
        "risk": risk,
        "weeks": weeks,
        "contracts": contracts,
        "shipments": shipments,
        "cbam_calculations": calculations,
        "remediation": remediation,
        "regulatory": regulatory,
        "audit": audit,
        "data_status": risk.get("data_status"),
    }
