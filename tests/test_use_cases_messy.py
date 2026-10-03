"""Use-case gate: OUCO messy-MTC demo stays fail-closed and license-honest."""
import csv
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UC = ROOT / "use_cases/ouco_mtc_messy"


def _load_runner():
    spec = importlib.util.spec_from_file_location(
        "messy_demo", UC / "run_messy_demo.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_messy_rows_block_then_remediate_to_ready():
    mod = _load_runner()
    with (UC / "messy_mtc_input.csv").open() as f:
        mtc = list(csv.DictReader(f))
    with (UC / "receipts_messy_sample.csv").open() as f:
        rcpt = list(csv.DictReader(f))
    assert len(mtc) == 5 and len(rcpt) == 4
    for row in mtc:
        rec = mod.run_row(row["row_id"], row["defect_kind"])
        assert rec["initial"] == "BLOCKED" and rec["remediated"] == "READY"
        assert rec["predecessor_preserved"] and rec["policy"] == "DECISION_POLICY_V1"
    for row in rcpt:
        rec = mod.run_row(row["receipt_id"], row["defect_kind"])
        assert rec["initial"] == "BLOCKED" and rec["remediated"] == "READY"


def test_receipt_parse_keeps_ambiguous_amounts_unparsed():
    """The typed extractor must leave messy receipt totals unresolved and
    name the defect - '1,9' never 19, '412 EUR' never 412."""
    mod = _load_runner()
    recs = mod.receipt_parse_check()
    by_kind = {r["defect_kind"]: r for r in recs}
    assert set(by_kind) == {"decimal_comma", "units_embedded",
                            "qty_mismatch", "duplicate"}
    assert by_kind["decimal_comma"]["total"] is None
    assert by_kind["decimal_comma"]["total_raw"] == "1,9"
    assert by_kind["units_embedded"]["total"] is None
    assert by_kind["units_embedded"]["total_raw"] == "412 EUR"
    # a clean numeric amount parses; the defect is the row, not the doc
    assert by_kind["qty_mismatch"]["total"] == 412.0
    assert by_kind["duplicate"]["duplicate_of"] is not None


def test_receipt_records_carry_no_unredacted_pii():
    """Receipt string fields pass through the PII patterns, so only
    redacted values can leave the parse step."""
    from app.document_ingest import extract_receipt_records
    text = ("| receipt_id | vendor | total |\n"
            "| --- | --- | --- |\n"
            "| RCPT-1 | ACME IEC 0123456789 | 412.00 |\n")
    out = extract_receipt_records(text, "r.pdf", "sha123")
    assert "0123456789" not in json.dumps(out["records"])


def test_ouco_catalog_is_link_only_and_names_redirect():
    cat = json.loads((UC / "ouco_material_image_catalog.json").read_text())
    assert cat["requested_url"] == "https://ouco-industry.com/material/to"
    assert "top-10-china-marine-crane-manufacturers-in-2023" in cat["resolved_url"]
    assert "No mill certificates" in cat["what_is_missing"]
    assert len(cat["images"]) >= 20
    assert all(u["url"].startswith("https://ouco-industry.com/wp-content/")
               for u in cat["images"])
    # no binaries copied alongside the catalog
    binaries = [p for p in UC.iterdir()
                if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".pdf")]
    assert binaries == []
    prov = json.loads((UC / "provenance.json").read_text())
    assert all(a["parent_source_url"] and a["synthetic_transform"]
               for a in prov["artifacts"])
