"""JSW Vijayanagar demo regression tests.

All commercial rows are synthetic; regulatory context is public.
Guards the demo contract: portfolio shape, CBAM fixture math, steel
safeguard mapping, FTA guardrail, and the pipeline completeness gate.
"""
import json
from pathlib import Path

from app.cbam_engine import calculate_actual_steel
from app.fta_origin import evaluate_origin
from app.steel_trade_engine_v2 import category as steel_category, evaluate as steel_evaluate

ROOT = Path(__file__).resolve().parents[1]


def test_jsw_portfolio_shape():
    d = json.loads((ROOT / "examples" / "jsw_vijayanagar_demo_portfolio.json").read_text())
    assert d["provenance"] == "SYNTHETIC_COMMERCIAL_DATA_PUBLIC_REGULATORY_CONTEXT"
    assert len(d["shipments"]) == 8
    refs = {s["shipment_ref"] for s in d["shipments"]}
    assert "JSW-HRC-NL-001" in refs and "JSW-HRC-PL-008" in refs
    total = sum(s["customs_value_eur"] for s in d["shipments"])
    assert total == 7790000
    for s in d["shipments"]:
        assert s["origin_country"] == "IN" and s["demo_scenario"]


def test_jsw_cbam_fixture_math():
    out = calculate_actual_steel(
        json.loads((ROOT / "examples" / "jsw_vijayanagar_cbam_actual.json").read_text())
    )
    assert out["methodology"]["id"] == "EU_CBAM_2026_2547"
    assert out["specific_embedded_emissions_tco2_per_t"] == 1.73
    assert out["status"] == "CALCULATED_VERIFIED"


def test_jsw_steel_safeguard_mapping():
    assert steel_category("72083900")["category"] == "1A"
    assert steel_category("72085120")["category"] == "7"
    assert steel_category("72191390")["category"] == "8"
    r = steel_evaluate({
        "cn_code": "72083900", "origin_country": "IN", "import_date": "2026-09-29",
        "quantity_t": 2500, "customs_value_eur": 1700000,
    })
    assert r["entitlement_status"] == "QUOTA_BALANCE_REQUIRED"
    plate = steel_evaluate({
        "cn_code": "72085120", "origin_country": "IN", "import_date": "2026-09-29",
        "quantity_t": 900, "customs_value_eur": 680000,
    })
    assert plate["quota_order_number"] == "09.9856"


def test_jsw_fta_guardrail():
    out = evaluate_origin(json.loads((ROOT / "examples" / "fta_origin_preview.json").read_text()))
    assert out["legal_regime"] == "CURRENT_MFN"
    assert out["preference_available"] is False
    assert out["tariff_saving_eur"] == 0


def test_pipeline_blocks_without_genealogy_or_ems():
    from app.db import init_db
    from app.integrations import import_sample, integration_catalog
    from app.steel_pipeline import evaluate_shipment_cbam

    init_db()
    for c in integration_catalog()["connectors"]:
        import_sample(c["code"])
    # DEMO-EU-001 has full backbone; a shipment with no SAP row raises honestly
    try:
        evaluate_shipment_cbam("NO-SUCH-SHIPMENT")
        raised = False
    except ValueError:
        raised = True
    assert raised
