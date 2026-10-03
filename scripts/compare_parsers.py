"""Parser comparison: PP-StructureV3 vs pypdf vs pdftotext baseline vs
firecrawl (URL-gated), plus polars CSV/XLSX column mapping. Synthetic
fixtures only - never reads data/client_data/ (local-only, untracked).

Usage: .venv/bin/python scripts/compare_parsers.py [--with-paddle]
  --with-paddle runs the heavy PP-StructureV3 model path (downloads models
  on first run, slow). Default skips V3 and shows its fail-closed shape via
  a stub so the script stays fast.
"""
from __future__ import annotations

import io
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import document_ingest as ing  # noqa: E402


def _sample_pdf_bytes() -> bytes:
    try:
        from pypdf import PdfReader  # noqa: F401
    except ImportError:
        return b""
    # Minimal one-page PDF with extractable text (no external fixtures).
    text = ("BT /F1 12 Tf 50 750 Td (CN 72221119 QTY 24.371 MT EUR 47823.69 "
            "2026-09-29 INDIA ANTWERP) Tj ET")
    body = (f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>")
    objs = [f"{i} 0 obj\n{o}\nendobj\n" for i, o in enumerate(
        ["<< /Type /Catalog /Pages 2 0 R >>",
         "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
         body,
         f"<< /Length {len(text)} >>\nstream\n{text}\nendstream",
         "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"], start=1)]
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = []
    for o in objs:
        offsets.append(out.tell())
        out.write(o.encode())
    xref = out.tell()
    out.write(f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode())
    for off in offsets:
        out.write(f"{off:010d} 00000 n \n".encode())
    out.write(f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\n"
              f"startxref\n{xref}\n%%EOF".encode())
    return out.getvalue()


def main() -> int:
    with_paddle = "--with-paddle" in sys.argv
    print("== PDF: PP-StructureV3 vs pypdf vs pdftotext vs firecrawl ==")
    pdf = _sample_pdf_bytes()
    if not pdf:
        print("pypdf not installed - install requirements first.")
        return 2
    for r in ing.compare_pdf_parsers(pdf, include_paddle=with_paddle):
        print(f"  {r['parser']:20s} ok={r.get('ok')} chars={r.get('chars')} "
              f"time_ms={r.get('time_ms')} cns={r.get('cns_found')} "
              f"code={r.get('code', '')}")
    if not with_paddle:
        print("  (V3 skipped: rerun with --with-paddle to run the model path)")
    print("== CSV via polars ==")
    csv = (b"transaction_id,po_number,cn_code,origin,destination,shipment_date,"
           b"quantity_t,line_value_eur\nTX-001,PO-1,72221119,IN,DE,2026-09-29,24.371,47823.69\n")
    r = ing.parse_csv_polars(csv)
    print(f"  {r['parser']} ok={r.get('ok')} rows={r.get('rows')} cols={r.get('columns')}")
    if r.get("ok"):
        m = ing.dataframe_candidates(r["frame"], "sample.csv")
        print(f"  mapped={m['mapped_columns']} candidates={len(m['candidates'])}")
    print("== XLSX via polars ==")
    try:
        from openpyxl import Workbook
        wb = Workbook(); ws = wb.active
        ws.append(["cn_code", "quantity_t", "line_value_eur", "origin", "shipment_date"])
        ws.append(["72221119", 24.371, 47823.69, "IN", "2026-09-29"])
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            path = f.name
        wb.save(path)
        r2 = ing.parse_excel_polars(Path(path).read_bytes())
        print(f"  {r2['parser']} ok={r2.get('ok')} rows={r2.get('rows')} "
              f"sheets={r2.get('sheets')} cols={r2.get('columns')}")
        if r2.get("ok"):
            m2 = ing.dataframe_candidates(r2["frame"], "sample.xlsx")
            print(f"  mapped={m2['mapped_columns']} candidates={len(m2['candidates'])}")
    except Exception as e:
        print(f"  xlsx skipped: {e}")
    print("== firecrawl URL path (expected gate without key) ==")
    r3 = ing.parse_pdf_firecrawl_url("")
    print(f"  firecrawl ok={r3.get('ok')} code={r3.get('code')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
