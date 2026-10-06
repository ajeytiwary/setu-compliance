from io import BytesIO

from openpyxl import Workbook

from app.document_lines import ingest_pdf, ingest_tabular


def test_csv_preserves_row_cells_and_converts_kg_to_tonnes():
    data = ("invoice_number,cn_code,quantity,quantity_unit,value,currency,"
            "origin_country,destination_country,import_date,heat_number,container_number\n"
            "INV-7,72085120,1250,KG,5000,EUR,IN,NL,2026-10-03,H-5,MSMU5815419\n").encode()
    out = ingest_tabular(data, "invoice.csv")
    line = out["lines"][0]
    assert out["ok"] and line["quantity_t"] == 1.25
    assert line["customs_value_eur"] == 5000
    assert line["field_provenance"]["cn_code"]["cell"] == "B2"
    assert line["field_provenance"]["cn_code"]["sha256"] == out["document_sha256"]
    assert line["heat_number"] == "H-5" and line["container_number"] == "MSMU5815419"
    assert line["issues"] == []


def test_ambiguous_currency_unit_and_non_eu_destination_block():
    data = ("invoice_number,cn_code,quantity,quantity_unit,value,currency,"
            "origin_country,destination_country,import_date\n"
            "INV-8,72085120,\"1,9\",KG,\"1,900\",USD,IN,US,2026-10-03\n").encode()
    line = ingest_tabular(data, "invoice.csv")["lines"][0]
    assert line["quantity_t"] is None
    assert line["customs_value_eur"] is None
    assert "NON_EU_DESTINATION" in line["issues"]
    assert "EUR_CONVERSION_REQUIRES_RATE_SNAPSHOT" in line["issues"]


def test_xlsx_retains_sheet_and_formula_is_flagged():
    wb = Workbook()
    ws = wb.active
    ws.title = "Invoices"
    ws.append(["invoice_number", "cn_code", "quantity", "quantity_unit",
               "value", "currency", "origin_country", "destination_country", "import_date"])
    ws.append(["INV-9", "72085120", 2, "MT", "=1000*2", "EUR", "IN", "DE", "2026-10-03"])
    buf = BytesIO()
    wb.save(buf)
    out = ingest_tabular(buf.getvalue(), "invoice.xlsx")
    assert out["lines"][0]["field_provenance"]["cn_code"]["sheet"] == "Invoices"
    assert out["lines"][0]["field_provenance"]["cn_code"]["cell"] == "B2"
    assert "VALUE_MISSING_OR_AMBIGUOUS" in out["lines"][0]["issues"]
    assert out["issues"][0]["code"] == "FORMULA_REQUIRES_REVIEW"


def test_pdf_with_no_text_fails_closed():
    from pypdf import PdfWriter
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    buf = BytesIO()
    writer.write(buf)
    out = ingest_pdf(buf.getvalue(), "scan.pdf")
    assert not out["ok"] and out["lines"] == []
    assert {i["code"] for i in out["issues"]} >= {"PDF_OCR_REQUIRED", "PDF_LINE_ASSOCIATION_UNVERIFIED"}


def test_upload_to_compile_blocks_unreviewed_fields():
    from app.content_pages import api_workflow_run_parse, api_workflow_run_compile
    data = ("invoice_number,cn_code,quantity,quantity_unit,value,currency,"
            "origin_country,destination_country,import_date\n"
            "INV-10,72085120,2,MT,1000,EUR,IN,NL,2026-10-03\n").encode()
    parsed = api_workflow_run_parse([("trade.csv", data)])
    line = parsed["documents"][0]["candidates"][0]
    assert line["field_provenance"]["invoice_number"]["cell"] == "A2"
    line["issues"] = ["INVOICE_NUMBER_MISSING"]
    result = api_workflow_run_compile({"lines": [line]})
    assert result["lines"][0]["decision"] == "BLOCKED"
    assert result["lines"][0]["blockers"][0]["code"] == "INVOICE_NUMBER_MISSING"


def test_unverified_evidence_has_visible_blocker():
    from app.content_pages import api_workflow_run_compile
    line = {
        "shipment_ref": "TX-VISIBLE-BLOCKER",
        "invoice_number": "INV-1", "cn_code": "72085120",
        "quantity_t": 2, "customs_value_eur": 1000,
        "origin_country": "IN", "destination_country": "NL",
        "import_date": "2026-10-03",
        "evidence": [{"id": "E-1", "evidence_type": "COMMERCIAL_INVOICE", "verified": False}],
    }
    result = api_workflow_run_compile({"lines": [line], "seed_demo_taric": True})
    row = result["lines"][0]
    assert row["decision"] == "BLOCKED"
    assert any(b["engine"] == "EVIDENCE" and b["code"] == "COMMERCIAL_INVOICE_UNVERIFIED"
               for b in row["blockers"])
