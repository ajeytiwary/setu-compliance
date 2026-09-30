"""Pilot dashboard regression tests.

The pilot dashboard (/pilot) is separate from the customer-facing website
(/) and the public demo (/demo). These tests guard the route registration,
the 12-week plan shape, the six data contracts, and the overview payload.
"""
from app.pilot import DATA_CONTRACTS, PILOT_WEEKS, pilot_overview


def test_pilot_plan_and_contracts_shape():
    assert [w["week"] for w in PILOT_WEEKS] == list(range(1, 13))
    assert len(DATA_CONTRACTS) == 6
    assert {c["id"] for c in DATA_CONTRACTS} == {
        "sap_sd", "sap_mm", "mes", "ems", "supplier_cbam", "verifier"}
    for w in PILOT_WEEKS:
        assert w["objective"] and w["exit"] and w["signal"]


def test_pilot_overview_shape():
    d = pilot_overview()
    for key in ("scope", "kpis", "weeks", "contracts", "shipments",
                "cbam_calculations", "remediation", "regulatory", "audit"):
        assert key in d, key
    assert len(d["weeks"]) == 12
    assert len(d["contracts"]) == 6
    assert all(w["status"] in ("SIGNAL_PRESENT", "NO_SIGNAL", "MANUAL_TRACKING")
               for w in d["weeks"])
    assert all(c["status"] in ("CONNECTED_ROWS", "NO_ROWS") for c in d["contracts"])
    assert "READY_FOR_SUBMISSION" in d["scope"]["notice"]
    assert d["kpis"]["shipments"] == len(d["shipments"])


def test_pilot_routes_registered():
    from app.main import app
    paths = {getattr(r, "path", None) for r in app.routes}
    assert "/pilot" in paths
    assert "/pilot.js" in paths
    assert "/api/pilot/overview" in paths
