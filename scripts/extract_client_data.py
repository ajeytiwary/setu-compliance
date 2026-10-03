"""Batch-extract data/client_data PDFs → sidecar files in the same folder.

Local-only: data/client_data/ is untracked; all outputs stay alongside the
source PDFs and are never committed. Uses the fast parser stack from
app.document_ingest (pypdf + pdftotext baseline); --with-paddle adds the
heavy PP-StructureV3 path (slow: ~1 min/file on CPU).

Per PDF <stem>.pdf writes:
  <stem>.extract.json  parser comparison (no full text), redacted preview,
                       PII codes, extracted candidates, typed receipt
                       records, step mapping, sha256
  <stem>.best.txt       full text of the best-pick parser (local-only)

Plus folder-level:
  _index.json           one row per PDF (parse status, chars, CNs, qty, value)
  _candidates.csv       extracted shipment candidates for pipeline runs
  _receipts.csv         one row per typed receipt record (raw + parsed +
                        per-row codes; unparseable amounts stay blank)

Usage:
  .venv/bin/python scripts/extract_client_data.py [--with-paddle] [--force]
"""
from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import document_ingest as ing

CLIENT_DIR = Path(__file__).resolve().parent.parent / "data" / "client_data"
PRIO = {"paddle-structure-v3": 3, "pypdf": 2, "pdftotext-baseline": 1}


def pick_best(comp: list[dict]) -> dict | None:
    """Best parse, or None.

    A parse with no text is never a win. Without this, a re-run without
    --with-paddle silently replaces a good paddle extraction (which finds CNs
    and tables) with an empty pypdf result, and still reports ok=True.
    Callers must treat None as a failure, not a fallback.
    """
    ok = [r for r in comp if r.get("ok") and (r.get("chars") or 0) > 0]
    if not ok:
        return None
    return max(ok, key=lambda r: (len(r.get("cns_found") or []),
                                  PRIO.get(r.get("parser"), 0),
                                  r.get("chars", 0)))


def one(pdf: Path, with_paddle: bool, force: bool) -> dict:
    out_json = pdf.with_suffix("").as_posix() + ".extract.json"
    out_txt = pdf.with_suffix("").as_posix() + ".best.txt"
    if Path(out_json).exists() and Path(out_txt).exists() and not force:
        row = json.loads(Path(out_json).read_text())["summary"]
        row["skipped"] = True
        # sidecars written before receipt extraction has no receipt fields
        row.setdefault("receipt_rows", 0)
        row.setdefault("receipt_codes", [])
        return row
    data = pdf.read_bytes()
    sha = hashlib.sha256(data).hexdigest()[:16]
    comp = ing.compare_pdf_parsers(data, include_paddle=with_paddle)
    best = pick_best(comp)
    # torch's caching allocator keeps the peak allocation of a large document
    # reserved, so the next giant in the batch starts with less free VRAM than
    # the first one had and can OOM on a file that would otherwise parse. Drop
    # the cached blocks and drop our own references before moving on.
    del data
    gc.collect()
    ing._release_gpu_cache()
    slim = [{k: r.get(k) for k in ("parser", "ok", "pages", "chars",
                                   "time_ms", "cns_found", "code", "reason")}
            for r in comp]
    if best is None:
        summary: dict = {"file": pdf.name, "sha16": sha, "ok": False,
                         "reason": "; ".join(r.get("code", "?") for r in comp)}
        Path(out_json).write_text(json.dumps(
            {"source": pdf.name, "sha256_16": sha, "parser_comparison": slim,
             "summary": summary}, indent=2))
        return summary
    text = best.get("text", "")
    for r in comp:
        r.pop("text", None)
    red, pii = ing.redact_preview(text)
    ext = ing.extract_candidates(text, pdf.name)
    steps = ing.map_to_steps(pdf.name, ext)
    receipts = ing.extract_receipt_records(text, pdf.name, sha)
    Path(out_txt).write_text(text)
    cand = ext["candidate"]
    summary = {"file": pdf.name, "sha16": sha, "ok": True,
               "best_parser": best.get("parser"),
               "chars": len(text), "pages": best.get("pages"),
               "cns": ext["cn_codes_found"][:5],
               "qty_t": cand["quantity_t"], "value_eur": cand["customs_value_eur"],
               "origin": cand["origin_country"], "pii": pii,
               "receipt_rows": receipts["rows"],
               "receipt_codes": receipts["codes"]}
    Path(out_json).write_text(json.dumps(
        {"source": pdf.name, "sha256_16": sha, "best_parser": best.get("parser"),
         "parser_comparison": slim, "redacted_preview": red, "pii_codes": pii,
         "extracted": ext, "receipts": receipts, "steps": steps,
         "summary": summary}, indent=2))
    return summary


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--with-paddle", action="store_true",
                    help="include PP-StructureV3 (slow on CPU)")
    ap.add_argument("--force", action="store_true", help="re-extract all")
    ap.add_argument("--only", nargs="*", default=None, help="PDF basenames")
    args = ap.parse_args()
    pdfs = sorted(CLIENT_DIR.glob("scribd-*.pdf"))
    if args.only:
        pdfs = [p for p in pdfs if p.name in args.only]
    print(f"{len(pdfs)} PDFs (paddle={'on' if args.with_paddle else 'off'})", flush=True)
    rows = []
    for i, p in enumerate(pdfs, 1):
        print(f"[{i}/{len(pdfs)}] {p.name} ...", flush=True)
        r = one(p, args.with_paddle, args.force)
        print(f"[{i}/{len(pdfs)}] {p.name}: ok={r.get('ok')} "
              f"parser={r.get('best_parser', '-')} chars={r.get('chars', 0)} "
              f"cns={r.get('cns', [])} receipts={r.get('receipt_rows', 0)} "
              f"rcpt_codes={r.get('receipt_codes', [])}", flush=True)
        rows.append(r)
    ok = sum(1 for r in rows if r.get("ok"))
    print(f"parsed {ok}/{len(rows)}")
    for r in rows:
        print(f"  {r['file']}: ok={r.get('ok')} "
              f"parser={r.get('best_parser', '-')} chars={r.get('chars', 0)} "
              f"cns={r.get('cns', [])} qty={r.get('qty_t')} "
              f"val={r.get('value_eur')} pii={r.get('pii', [])} "
              f"receipts={r.get('receipt_rows', 0)} "
              f"rcpt_codes={r.get('receipt_codes', [])}")
    (CLIENT_DIR / "_index.json").write_text(json.dumps(rows, indent=2))
    with open(CLIENT_DIR / "_candidates.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["source", "cn_code", "quantity_t", "customs_value_eur",
                    "origin_country", "best_parser"])
        for r in rows:
            if not r.get("ok"):
                continue
            j = json.loads((CLIENT_DIR / (Path(r["file"]).stem + ".extract.json")).read_text())
            c = j["extracted"]["candidate"]
            w.writerow([r["file"], c["cn_code"], c["quantity_t"],
                        c["customs_value_eur"], c["origin_country"],
                        r.get("best_parser")])
    with open(CLIENT_DIR / "_receipts.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["record_key", "source", "receipt_id", "vendor", "total_raw",
                    "total", "qty_raw", "quantity", "date", "codes",
                    "duplicate_of"])
        for r in rows:
            if not r.get("ok"):
                continue
            j = json.loads((CLIENT_DIR / (Path(r["file"]).stem + ".extract.json")).read_text())
            for rec in j.get("receipts", {}).get("records", []):
                w.writerow([rec["record_key"], r["file"], rec["receipt_id"],
                            rec["vendor"], rec["total_raw"],
                            "" if rec["total"] is None else rec["total"],
                            rec["qty_raw"],
                            "" if rec["quantity"] is None else rec["quantity"],
                            rec["date"], "; ".join(rec["codes"]),
                            rec["duplicate_of"] or ""])
    print("wrote _index.json + _candidates.csv + _receipts.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
