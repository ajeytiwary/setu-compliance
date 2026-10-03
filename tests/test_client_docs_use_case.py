"""Use-case gate: client-docs EU-bound demo stays fail-closed and redacted."""
import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UC = ROOT / "use_cases/client_docs_eu_bound"

PII_PATTERNS = [
    r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",          # PAN shape
    r"\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]",    # GSTIN prefix shape
    r"\b\d{4} ?\d{4} ?\d{4}\b",            # bank-account-ish runs
    r"IEC\s*\d{10}", r"\bCIN\b",
    r"MSMU\d+|TGHU\d+|FSCU\d+",            # container numbers
    r"seal\s*(no\.?|number)", r"CHA\b|AD240425019230O|ABCCS9120M|AAACA",
]


def _load_runner():
    spec = importlib.util.spec_from_file_location(
        "client_docs_demo", UC / "run_client_docs_demo.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_redacted_extracts_run_full_pipeline():
    mod = _load_runner()
    ships = json.loads((UC / "redacted_shipments.json").read_text())["shipments"]
    assert {s["shipment_ref"] for s in ships} == {
        "CLIENT-AMBICA-01", "CLIENT-APOLLO-01"}
    ambica = next(s for s in ships if s["shipment_ref"] == "CLIENT-AMBICA-01")
    assert ambica["cn_code"] == "72221119"
    assert ambica["steel_category"]["india_order_number"] == "09.9890"
    assert abs(sum(li["qty_mts"] for li in ambica["line_items"])
               - ambica["pipeline_quantity_t"]) < 0.001
    # phase A blocks, phase B: steel case READY, non-steel documents boundary
    for s in ships:
        ref = s["shipment_ref"]
        states_a = {k: mod.ev.evaluate_requirement(v, as_of=mod.AS_OF)["state"]
                    for k, v in mod.PHASE_A[ref].items()}
        assert set(states_a.values()) == {"UNVERIFIED"}
        states_b = {k: mod.ev.evaluate_requirement(v, as_of=mod.AS_OF)["state"]
                    for k, v in mod.PHASE_B[ref].items()}
        assert set(states_b.values()) == {"VALID"}
        comp_b = mod.compile_shipment(mod.shipment_payload(s, "B"))
        assert comp_b["decision"] == mod.EXPECTED_COMPILER_B[ref]
        ent = mod.compile_active_entitlement(mod.entitlement_payload(s))
        assert ent["decision"] == "ENTITLED"
        assert ent["steel_measure"]["legal_basis"]
    assert mod.compile_shipment(
        mod.shipment_payload(ambica, "A"))["decision"] == "BLOCKED"


def test_no_binaries_no_pii_and_provenance():
    binaries = [p for p in UC.iterdir()
                if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".pdf")]
    assert binaries == []
    text = "".join(
        (UC / f).read_text()
        for f in ("redacted_shipments.json", "mtc_shape.json", "README.md",
                  "run_client_docs_demo.py"))
    for pat in PII_PATTERNS:
        assert not re.search(pat, text, re.IGNORECASE), pat
    prov = json.loads((UC / "provenance.json").read_text())
    assert all(a["parent_source_url"] and a["synthetic_transform"]
               for a in prov["artifacts"])
    assert "Scenario demo only" in prov["license_note"]
