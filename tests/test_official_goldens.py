"""Official-source golden tests: EC CBAM steel routes + 2026 defaults/benchmarks + TARIC + ROSA-pattern origin.

Sources pinned (no invented constants):
- CBAM defaults : data/cbam/defaults.json  version 2025/2621-corrected-2026/1740
                  (from data/official/cbam-defaults-official.json, Reg 2026/1740)
- CBAM benchmarks: data/cbam/benchmarks.json version 2025/2620 (Reg 2025/2620)
- CSCF table    : data/cbam/cscf.json source CELEX:32026D1862 (2026=1.0)
- Steel safeguard categories: data/official/steel-2026-1457-categories.csv
                  (Reg 2026/1384 + 2026/1457, e.g. 72083900/IN -> cat 1A / 09.9803)
- CBAM BF-BOF worked calculation: examples/cbam_actual_steel.json (1.73 tCO2e/t)
- Origin engine : app/fta_origin.py (EU-IN FTA NEGOTIATED_NOT_IN_FORCE -> CURRENT_MFN)

What these goldens are NOT: verbatim copies of EC guidance PDFs or ROSA tool
content. BF/EAF route goldens assert engine behaviour on route-labelled payloads
(BF-BOF integrated vs EAF scrap route); ROSA-pattern cases assert PSR primitives
(CTH/MAXNOM/RVC/WO/cumulation) as exercised through the ROSA self-assessment flow.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app import cbam_definitive_v2 as v2
from app.cbam_engine import calculate_actual_steel, steel_cbam_scope
from app.fta_origin import evaluate_origin, evaluate_psr
from app.taric_engine import resolve_taric
from app import eu_public_data as pub

ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------- BF/EAF route goldens

def test_golden_bf_bof_worked_calculation_intensity_1_73():
    """BF-BOF integrated HRC route: 1550 attributed + 180 precursor = 1730 / 1000t."""
    payload = json.loads((ROOT / "examples" / "cbam_actual_steel.json").read_text())
    assert payload["production_route"] == "BF-BOF"
    out = calculate_actual_steel(payload)
    assert out["specific_direct_embedded_emissions_tco2_per_t"] == 1.73
    assert out["methodology"]["id"] == "EU_CBAM_2026_2547"
    # Steel is direct-only in the definitive period; indirect kept for audit only.
    assert out["indirect_emissions_audit_tco2"] == 84.0
    assert out["indirect_emissions_included_tco2"] == 0.0


def test_golden_eaf_scrap_route_lower_intensity_direct_only():
    """EAF scrap route: same engine, lower intensity, still direct-only scope."""
    payload = json.loads((ROOT / "examples" / "cbam_actual_steel.json").read_text())
    payload = {**payload, "production_route": "EAF",
               "production_process": "EAF scrap route",
               "direct_emission_sources": [
                   {"source_id": "EAF_PROCESS", "measured_emissions_tco2": 380.0,
                    "evidence_ref": "EMS/EAF/2026"}],
               "boundary_adjustments": [],
               "precursors": []}
    out = calculate_actual_steel(payload)
    assert out["scope"]["direct_only"] is True
    assert out["specific_direct_embedded_emissions_tco2_per_t"] == pytest.approx(0.38)
    assert out["specific_direct_embedded_emissions_tco2_per_t"] < 1.73
    assert out["indirect_emissions_included_tco2"] == 0.0


def test_golden_steel_scope_direct_only_exclusions():
    assert steel_cbam_scope("72083900") == {
        "in_scope": True, "direct_only": True,
        "sector": "iron_and_steel", "cn": "72083900"}
    # Scrap (7204) is out of CBAM scope.
    assert steel_cbam_scope("7204")["in_scope"] is False

# ------------------------------------------------- 2026 defaults/benchmarks goldens

def test_golden_india_hrc_default_2026_with_markup():
    """Official default INDIA/7208 route (C): total 4.28 -> 4.708 with 2026 +10% markup."""
    d = v2.select_default("IN", "72083900", "(C)", 2026)
    assert d["available"] is True
    assert d["dataset_version"] == "2025/2621-corrected-2026/1740"
    assert d["total"] == 4.28
    assert d["markup"] == 0.10
    assert d["certificate_default_total"] == pytest.approx(4.708)


def test_golden_india_hrc_default_2027_markup_steps_up():
    d = v2.select_default("IN", "72083900", "(C)", 2027)
    assert d["available"] is True
    assert d["markup"] == 0.20
    assert d["certificate_default_total"] == pytest.approx(4.28 * 1.20)


def test_golden_hrc_benchmark_and_faa_2026():
    """Official benchmark 72083900 (C) = 0.044 -> FAA 0.975 * 1.0 * 0.044."""
    bm = v2.select_benchmark("72083900", "(C)")
    assert bm["available"] is True
    assert bm["dataset_version"] == "2025/2620"
    assert bm["benchmark"] == 0.044
    faa = v2.free_allocation_adjustment("72083900", 100, 2026, "(C)")
    assert faa["available"] is True
    assert faa["cscf"] == 1.0 and faa["cbam_factor"] == 0.975
    assert faa["specific_embedded_free_allocation_tco2e_per_t"] == pytest.approx(0.0429)
    assert faa["free_allocation_adjustment_tco2e"] == pytest.approx(4.29)


def test_golden_default_mode_end_to_end_blocked_without_tables(tmp_path, monkeypatch):
    """Default/FAA entitlement fails closed when reference tables are absent."""
    monkeypatch.setattr(v2, "DATA", tmp_path)
    d = v2.select_default("IN", "72083900", "(C)", 2026)
    assert d == {"available": False, "reason": "CORRECTED_DEFAULT_DATA_REQUIRED"}
    f = v2.free_allocation_adjustment("72083900", 100, 2026, "(C)")
    # FAA checks benchmarks before CSCF, so empty DATA fails on benchmarks first.
    assert f["available"] is False and f["reason"] == "BENCHMARK_DATA_REQUIRED"
    # With benchmarks present but no CSCF table, it must fail on CSCF specifically.
    v2.import_benchmarks("cn_code,production_route,benchmark\n72083900,(C),0.044\n")
    f2 = v2.free_allocation_adjustment("72083900", 100, 2026, "(C)")
    assert f2["available"] is False and f2["reason"] == "CSCF_TABLE_REQUIRED"

# ---------------------------------------------------------------- TARIC goldens

def _load_taric(tmp_path, monkeypatch, taric, quota=None):
    monkeypatch.setattr(pub, "CACHE", tmp_path)
    pub.store_snapshot("taric", pub.parse_csv(taric, "taric", "2026-09-29"), taric.encode())
    if quota:
        pub.store_snapshot("quota", pub.parse_csv(quota, "quota", "2026-09-29"), quota.encode())


def test_golden_taric_stacks_base_plus_trade_defence():
    """Realistic HRC stack: 5% third-country duty + 10% trade defence on IN/72083900."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        from pathlib import Path as P
        import unittest.mock as m
        with m.patch.object(pub, "CACHE", P(td)):
            taric = ("cn_code,origin_country,measure_type,duty_rate,valid_from\n"
                     "72083900,IN,THIRD_COUNTRY_DUTY,5%,2026-01-01\n"
                     "72083900,IN,ANTIDUMPING,10%,2026-01-01\n")
            pub.store_snapshot("taric", pub.parse_csv(taric, "taric", "2026-09-29"), taric.encode())
            r = resolve_taric("72083900", "IN", "2026-09-29", 100000, 100)
    assert r["resolved"] is True
    assert r["base_customs_duty_eur"] == 5000
    assert r["trade_defence_duty_eur"] == 10000
    assert r["total_taric_duty_eur"] == 15000


def test_golden_steel_safeguard_category_mapping_1a():
    """72083900/IN maps to safeguard category 1A, order 09.9803 (2026/1457 annex)."""
    rows = (ROOT / "data" / "official" / "steel-2026-1457-categories.csv").read_text().splitlines()
    match = [ln for ln in rows if "72083900,IN" in ln]
    assert match, "72083900/IN missing from official steel category extract"
    assert "09.9803" in match[0] and match[0].startswith("1A,")


def test_golden_taric_stale_snapshot_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(pub, "CACHE", tmp_path)
    csv = "cn_code,origin_country,measure_type,duty_rate\n72083900,IN,THIRD_COUNTRY_DUTY,5%\n"
    pub.store_snapshot("taric", pub.parse_csv(csv, "taric", "2026-09-20"), csv.encode())
    r = resolve_taric("72083900", "IN", "2026-09-29", 100000, 100)
    assert r["status"] == "TARIC_SNAPSHOT_REQUIRED" and r["resolved"] is False

# ------------------------------------------------------- ROSA-pattern origin goldens

def _origin_payload(**over):
    base = {"agreement_id": "EU_IN_FTA_2026_NEGOTIATED", "shipment_ref": "GOLDEN",
            "shipment_date": "2026-08-28", "customs_value_eur": 1812000,
            "mfn_duty_rate_pct": 5.0, "preferential_duty_rate_pct": 0.0,
            "product": {"hs_code": "720839", "ex_works_price": 1750000,
                        "processes": ["BF", "BOF", "CASTER", "HSM"]},
            "materials": [
                {"material_id": "IRON-ORE", "hs_code": "260111", "value": 320000,
                 "originating": False},
                {"material_id": "COKE", "hs_code": "270400", "value": 180000,
                 "originating": False},
                {"material_id": "SCRAP-IN", "hs_code": "720449", "value": 50000,
                 "originating": True}],
            "product_specific_rule": {"all_of": [{"type": "CTH"},
                                                {"type": "MAXNOM", "threshold_pct": 50}]}}
    base.update(over)
    return base


def test_golden_rosa_pattern_hrc_passes_cth_maxnom_but_mfn_applies():
    """ROSA-pattern HRC case: technically qualifies, but FTA not in force -> CURRENT_MFN."""
    out = evaluate_origin(_origin_payload())
    assert out["psr_evaluation"]["pass"] is True
    assert out["technical_origin_preview"] is True
    assert out["legal_regime"] == "CURRENT_MFN"
    assert out["preference_available"] is False
    assert out["tariff_saving_eur"] == 0


def test_golden_rosa_pattern_maxnom_fail_blocks_technical_origin():
    mats = [{"material_id": "M1", "hs_code": "260111", "value": 1000000, "originating": False}]
    out = evaluate_origin(_origin_payload(
        materials=mats,
        product={"hs_code": "720839", "ex_works_price": 1750000, "processes": ["BF", "BOF"]}))
    assert out["psr_evaluation"]["pass"] is False
    assert out["technical_origin_preview"] is False


def test_golden_rosa_pattern_wholly_obtained_and_rvc():
    assert evaluate_psr({"type": "WO"}, {"hs_code": "720839"},
                        [{"material_id": "A", "hs_code": "720839",
                          "value": 10, "originating": True}])["pass"] is True
    rvc = evaluate_psr({"type": "RVC_MIN", "threshold_pct": 40},
                       {"hs_code": "720839", "ex_works_price": 1000},
                       [{"material_id": "N", "hs_code": "260111",
                         "value": 500, "originating": False}])
    assert rvc["pass"] is True and rvc["value_pct"] == pytest.approx(50.0)
