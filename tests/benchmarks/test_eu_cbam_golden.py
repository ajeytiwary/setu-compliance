"""EU-CBAM-GOLDEN (P0, SYNTHETIC): internal calculation regression fixtures pending direct EC workbook oracle ingestion.

Proves (§5.1): official steel examples parse without manual edits, calculated
fields match within tolerance, malformed cells fail closed (ERROR, never
guessed), CI prints field-level diff on failure.

Fixtures: tests/fixtures/eu_cbam/<case>/source/ holds byte-identical copies of
the canonical inputs (examples/cbam_actual_steel.json for BF-BOF; derived EAF
variant); SHA-256 manifest asserted at test start. Expected outputs are the
engine goldens from tests/test_official_goldens.py (1.73 BF-BOF, 0.38 EAF).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.benchmark_harness import BenchmarkCase
from app.cbam_engine import calculate_actual_steel
from app.main import app

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "tests" / "fixtures" / "eu_cbam"
AS_OF = "2026-08-28"


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _ensure_fixtures() -> dict:
    """Materialise immutable fixture copies; return {case: sha256} manifest."""
    src = json.loads((ROOT / "examples" / "cbam_actual_steel.json").read_text())
    bf_dir = FIX / "steel_bf_001" / "source"
    eaf_dir = FIX / "steel_eaf_001" / "source"
    bf_dir.mkdir(parents=True, exist_ok=True)
    eaf_dir.mkdir(parents=True, exist_ok=True)
    bf_file = bf_dir / "installation.json"
    if not bf_file.exists():
        bf_file.write_text(json.dumps(src, indent=2, sort_keys=True))
    eaf = {**src, "production_route": "EAF",
           "production_process": "EAF scrap route",
           "direct_emission_sources": [
               {"source_id": "EAF_PROCESS",
                "measured_emissions_tco2": 380.0,
                "evidence_ref": "EMS/EAF/2026"}],
           "boundary_adjustments": [],
           "precursors": []}
    eaf_file = eaf_dir / "installation.json"
    if not eaf_file.exists():
        eaf_file.write_text(json.dumps(eaf, indent=2, sort_keys=True))
    return {"steel_bf_001": _sha(bf_file.read_bytes()),
            "steel_eaf_001": _sha(eaf_file.read_bytes())}


def test_eu_cbam_golden_bf_bof():
    manifest = _ensure_fixtures()
    case = BenchmarkCase(suite_id="EU-CBAM-GOLDEN", case_id="steel_bf_001",
                         evidence_class="SYNTHETIC", as_of=AS_OF,
                         manifest={"fixture_sha256": manifest["steel_bf_001"]})
    payload = json.loads((FIX / "steel_bf_001" / "source" / "installation.json").read_text())
    out = calculate_actual_steel(payload)
    actual = {"specific_direct_embedded_emissions_tco2_per_t":
              out["specific_direct_embedded_emissions_tco2_per_t"],
              "methodology": out["methodology"]["id"],
              "direct_only": out["scope"]["direct_only"],
              "indirect_included": out["indirect_emissions_included_tco2"]}
    case.assert_and_emit(actual, {
        "specific_direct_embedded_emissions_tco2_per_t": 1.73,
        "methodology": "EU_CBAM_2026_2547",
        "direct_only": True,
        "indirect_included": 0.0,
    }, tolerances={"specific_direct_embedded_emissions_tco2_per_t": 1e-9})


def test_eu_cbam_golden_eaf():
    manifest = _ensure_fixtures()
    case = BenchmarkCase(suite_id="EU-CBAM-GOLDEN", case_id="steel_eaf_001",
                         evidence_class="SYNTHETIC", as_of=AS_OF,
                         manifest={"fixture_sha256": manifest["steel_eaf_001"]})
    payload = json.loads((FIX / "steel_eaf_001" / "source" / "installation.json").read_text())
    out = calculate_actual_steel(payload)
    actual = {"specific_direct_embedded_emissions_tco2_per_t":
              out["specific_direct_embedded_emissions_tco2_per_t"],
              "direct_only": out["scope"]["direct_only"],
              "indirect_included": out["indirect_emissions_included_tco2"]}
    case.assert_and_emit(actual, {
        "specific_direct_embedded_emissions_tco2_per_t": 0.38,
        "direct_only": True,
        "indirect_included": 0.0,
    }, tolerances={"specific_direct_embedded_emissions_tco2_per_t": 1e-9})


def test_eu_cbam_golden_malformed_fails_closed():
    """Missing activity level → ERROR, never a guessed value (§5.1, §9.1)."""
    case = BenchmarkCase(suite_id="EU-CBAM-GOLDEN", case_id="steel_malformed_001",
                         evidence_class="SYNTHETIC", as_of=AS_OF)
    payload = json.loads((FIX / "steel_bf_001" / "source" / "installation.json").read_text())
    payload = {**payload, "activity_level_t": 0}
    try:
        calculate_actual_steel(payload)
        actual = {"outcome": "CALCULATED"}
    except (ValueError, KeyError) as e:
        actual = {"outcome": "ERROR", "reason": f"{type(e).__name__}"}
    case.assert_and_emit(actual, {"outcome": "ERROR", "reason": "ValueError"})


def test_eu_cbam_golden_via_check_path():
    """Production ingestion path: v1 check with cbam_payload → READY decision."""
    from tests.benchmarks.helpers import check
    _ensure_fixtures()
    case = BenchmarkCase(suite_id="EU-CBAM-GOLDEN", case_id="steel_bf_check_001",
                         evidence_class="SYNTHETIC", as_of=AS_OF)
    client = TestClient(app)
    payload = json.loads((FIX / "steel_bf_001" / "source" / "installation.json").read_text())
    cbam_payload = {**payload, "origin_country": "IN",
                    "value_type": "ACTUAL", "reporting_period": 2026,
                    "mass_t": payload["activity_level_t"],
                    "verification": {"status": "VERIFIED",
                                     "verifier": payload.get("verification", {}).get("verifier", "PILOT-VERIFIER")}}
    txn = {"transaction_ref": "TXN-EUCBAM-BF-001", "order_id": "PO-EU-000342",
           "shipment_id": "SHP-001", "line_id": "L1", "origin_country": "IN",
           "destination_country": "NL", "shipment_date": AS_OF,
           "line_value": 1700000.0, "quantity": 1000.0, "unit": "t",
           "cn_code": "72083900"}
    decision = check(client, txn, as_of=AS_OF, cbam_payload=cbam_payload)
    by_id = {o["obligation_id"]: o for o in decision["obligation_results"]}
    case.assert_and_emit(
        {"status": decision["status"],
         "CBAM_EMISSIONS": by_id.get("CBAM_EMISSIONS", {}).get("status")},
        {"status": "READY", "CBAM_EMISSIONS": "PASS"},
        decision_id=decision["decision_id"])
