"""Synthetic tests for typed receipt-record extraction.

app.document_ingest.extract_receipt_records turns paddle markdown pipe
tables / CSV blocks into one typed record per row, keeping the raw cell
next to a parsed number and a named code. Fail-closed: ambiguous amounts
stay None and are named, never guessed. Pure-CPU, no paddle import.

Defect shapes mirror use_cases/ouco_mtc_messy/receipts_messy_sample.csv.
"""
import pytest

from app.document_ingest import extract_receipt_records

SHA = "abc123def4567890"


def _cells(spec) -> list:
    """Cell list from a sequence, or a comma string (quoted cells respected)."""
    if not isinstance(spec, str):
        return [str(c) for c in spec]
    out, buf, quoted = [], "", False
    for ch in spec:
        if ch == '"':
            quoted = not quoted
        elif ch == "," and not quoted:
            out.append(buf.strip())
            buf = ""
        else:
            buf += ch
    out.append(buf.strip())
    return out


def pipe(header, *rows) -> str:
    """Markdown pipe table; header and each row are cell specs."""
    lines = ["| " + " | ".join(_cells(header)) + " |"]
    for r in rows:
        lines.append("| " + " | ".join(_cells(r)) + " |")
    return "\n".join(lines) + "\n"


# --- happy path ---

def test_clean_pipe_table_yields_typed_records():
    text = pipe("receipt_id,vendor,total,qty",
                "RCPT-10,OUCO chandlery,412.00,2")
    out = extract_receipt_records(text, "receipts.pdf", SHA)
    assert out["codes"] == []
    assert out["rows"] == 1
    r = out["records"][0]
    assert r["receipt_id"] == "RCPT-10"
    assert r["vendor"] == "OUCO chandlery"
    assert r["total"] == 412.0 and r["total_raw"] == "412.00"
    assert r["quantity"] == 2.0 and r["qty_raw"] == "2"
    assert r["codes"] == []
    assert r["record_key"] == f"{SHA}:0"
    assert r["duplicate_of"] is None


def test_multiple_rows_and_separator_row_skipped():
    text = pipe("receipt_id,vendor,total,qty",
                "RCPT-10,OUCO,412.00,2",
                "RCPT-11,OUCO,120.50,1")
    out = extract_receipt_records(text, "r.pdf", SHA)
    assert out["rows"] == 2
    assert [r["record_key"] for r in out["records"]] == [f"{SHA}:0", f"{SHA}:1"]
    assert all(r["duplicate_of"] is None for r in out["records"])


def test_unmapped_columns_kept_in_extra():
    text = pipe("receipt_id,vendor,total,po_number",
                "RCPT-10,OUCO,412.00,PO-77")
    out = extract_receipt_records(text, "r.pdf", SHA)
    assert out["records"][0]["extra"] == {"po_number": "PO-77"}


def test_missing_total_column_yields_missing_code():
    text = pipe("receipt_id,vendor,qty", "RCPT-10,OUCO,2")
    out = extract_receipt_records(text, "r.pdf", SHA)
    r = out["records"][0]
    assert r["total"] is None and r["total_raw"] is None
    assert "RECEIPT_TOTAL_MISSING" in r["codes"]
    assert r["quantity"] == 2.0


# --- defect shapes: fail closed, never guess ---

def test_decimal_comma_total_never_becomes_19():
    text = pipe("receipt_id,vendor,total,qty", "RCPT-01,OUCO,1,9,2")
    # comma inside the total cell is ambiguous -> keep raw, code it
    text = pipe("receipt_id,vendor,total,qty", "RCPT-01,OUCO,\"1,9\",2")
    out = extract_receipt_records(text, "r.pdf", SHA)
    r = out["records"][0]
    assert r["total"] is None
    assert r["total_raw"] == "1,9"
    assert "RECEIPT_TOTAL_DECIMAL_COMMA" in r["codes"]


def test_thousands_separator_is_still_decimal_comma_code():
    text = pipe("receipt_id,vendor,total,qty", "RCPT-01,OUCO,\"1,900\",2")
    out = extract_receipt_records(text, "r.pdf", SHA)
    assert out["records"][0]["total"] is None
    assert "RECEIPT_TOTAL_DECIMAL_COMMA" in out["records"][0]["codes"]


def test_units_embedded_total():
    text = pipe("receipt_id,vendor,total,qty", "RCPT-02,OUCO,\"412 EUR\",2")
    out = extract_receipt_records(text, "r.pdf", SHA)
    r = out["records"][0]
    assert r["total"] is None and r["total_raw"] == "412 EUR"
    assert "RECEIPT_TOTAL_UNITS_EMBEDDED" in r["codes"]


def test_units_embedded_qty():
    text = pipe("receipt_id,vendor,total,qty", "RCPT-02,OUCO,412.00,\"2 MT\"")
    out = extract_receipt_records(text, "r.pdf", SHA)
    r = out["records"][0]
    assert r["quantity"] is None and r["qty_raw"] == "2 MT"
    assert "RECEIPT_QTY_UNITS_EMBEDDED" in r["codes"]
    assert r["total"] == 412.0


def test_qty_mismatch_range_is_unparseable():
    text = pipe("receipt_id,vendor,total,qty", "RCPT-03,OUCO,412.00,\"2 vs 3\"")
    out = extract_receipt_records(text, "r.pdf", SHA)
    r = out["records"][0]
    assert r["quantity"] is None
    assert "RECEIPT_QTY_UNPARSEABLE" in r["codes"]


def test_duplicate_posted_twice_flags_and_points():
    text = pipe("receipt_id,vendor,total,qty",
                "RCPT-04,OUCO,412.00,2",
                "RCPT-04,OUCO,412.00,2")
    out = extract_receipt_records(text, "r.pdf", SHA)
    assert out["rows"] == 2
    first, second = out["records"]
    assert first["codes"] == [] and first["duplicate_of"] is None
    assert "RECEIPT_DUPLICATE" in second["codes"]
    assert second["duplicate_of"] == f"{SHA}:0"


def test_distinct_ids_same_amounts_not_duplicates():
    text = pipe("receipt_id,vendor,total,qty",
                "RCPT-20,OUCO,412.00,2",
                "RCPT-21,OUCO,412.00,2")
    out = extract_receipt_records(text, "r.pdf", SHA)
    assert all(r["duplicate_of"] is None for r in out["records"])
    assert all("RECEIPT_DUPLICATE" not in r["codes"] for r in out["records"])


def test_duplicate_without_receipt_id_uses_vendor_total_qty_identity():
    text = pipe("vendor,total,qty", "OUCO,412.00,2", "OUCO,412.00,2")
    out = extract_receipt_records(text, "r.pdf", SHA)
    assert out["records"][1]["duplicate_of"] == f"{SHA}:0"
    assert "RECEIPT_DUPLICATE" in out["records"][1]["codes"]


# --- table detection boundaries ---

def test_cn_quantity_table_is_not_read_as_receipts():
    """A CN line-item table (no receipt id / vendor) stays with
    extract_candidates, so receipt totals never get invented from it."""
    text = pipe("sr,cn_code,quantity_t,customs_value_eur",
                "1,84818081,10.5,41200.00")
    out = extract_receipt_records(text, "mtc.pdf", SHA)
    assert out["rows"] == 0
    assert out["codes"] == ["NO_RECEIPT_TABLE"]


def test_plain_text_without_table():
    out = extract_receipt_records("Invoice 412 EUR paid at the office.", "n.txt", SHA)
    assert out["records"] == []
    assert out["codes"] == ["NO_RECEIPT_TABLE"]


def test_bare_name_column_is_not_a_vendor():
    """'name' alone is too loose - an item-description table must not be
    read as a receipt table (vendor would be invented from the description)."""
    text = pipe(["name", "total", "qty"], ["HR Coil 10mm", "412.00", "2"])
    out = extract_receipt_records(text, "items.pdf", SHA)
    assert out["rows"] == 0
    assert out["codes"] == ["NO_RECEIPT_TABLE"]


def test_empty_input():
    out = extract_receipt_records("", "n.pdf", SHA)
    assert out["rows"] == 0 and out["codes"] == ["NO_RECEIPT_TABLE"]
    assert out["records"] == []


def test_header_only_table_is_no_receipt_rows():
    text = pipe("receipt_id,vendor,total,qty")
    out = extract_receipt_records(text, "r.pdf", SHA)
    assert out["codes"] == ["NO_RECEIPT_ROWS"] and out["rows"] == 0


def test_header_aliases_recognised():
    text = pipe("Invoice No,Supplier,Amount EUR,Quantity",
                "INV-9,Acme Ltd,1200.00,3")
    out = extract_receipt_records(text, "r.pdf", SHA)
    r = out["records"][0]
    assert r["receipt_id"] == "INV-9"
    assert r["vendor"] == "Acme Ltd"
    assert r["total"] == 1200.0
    assert r["quantity"] == 3.0


def test_csv_block_path():
    text = ("receipt_id,vendor,total,qty\n"
            "RCPT-30,OUCO,412.00,2\n")
    out = extract_receipt_records(text, "r.csv", SHA)
    assert out["rows"] == 1
    assert out["records"][0]["total"] == 412.0


def test_date_column_mapped():
    text = pipe("receipt_id,vendor,total,date", "RCPT-10,OUCO,412.00,2026-08-01")
    out = extract_receipt_records(text, "r.pdf", SHA)
    assert out["records"][0]["date"] == "2026-08-01"


# --- PII boundary ---

def test_pii_redacted_in_string_fields():
    text = pipe("receipt_id,vendor,total", "RCPT-10,ACME IEC 0123456789,412.00")
    out = extract_receipt_records(text, "r.pdf", SHA)
    v = out["records"][0]["vendor"]
    assert "0123456789" not in v
    assert "[REDACTED:IEC]" in v


def test_key_falls_back_to_source_without_sha():
    out = extract_receipt_records(pipe("receipt_id,total", "RCPT-1,10.00"),
                                  "invoice.pdf")
    assert out["records"][0]["record_key"] == "invoice.pdf:0"
    assert out["sha16"] == ""


def test_ragged_row_shorter_than_mapping_does_not_crash():
    text = pipe("receipt_id,vendor,total,qty", "RCPT-40,OUCO")
    out = extract_receipt_records(text, "r.pdf", SHA)
    r = out["records"][0]
    assert r["receipt_id"] == "RCPT-40"
    assert r["total"] is None and "RECEIPT_TOTAL_MISSING" in r["codes"]


def test_blank_row_skipped():
    text = pipe("receipt_id,vendor,total,qty",
                "RCPT-10,OUCO,412.00,2",
                ",,,", "RCPT-11,OUCO,10.00,1")
    out = extract_receipt_records(text, "r.pdf", SHA)
    assert out["rows"] == 2
    assert [r["record_key"] for r in out["records"]] == [f"{SHA}:0", f"{SHA}:1"]


def test_negative_total_allowed():
    out = extract_receipt_records(pipe("receipt_id,total", "RCPT-C,-50.25"),
                                  "r.pdf", SHA)
    assert out["records"][0]["total"] == -50.25


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
