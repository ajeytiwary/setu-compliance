"""Deterministic, review-only PDF observations with source coordinates.

Observations never imply that a document is authentic or that a shipment is
ready. The extractor favours omissions over cross-row joins.
"""
from __future__ import annotations

import hashlib
import io
import re
import subprocess
import time
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation
from pathlib import Path

from pypdf import PdfReader

MAX_PAGES = 50
MAX_BYTES = 8 * 1024 * 1024
WORD_LIMIT = 250_000
CONTAINER = re.compile(r"\b[A-Z]{4}\d{7}\b")
INVOICE = re.compile(r"\b(?:SPR\d{4}E\d{4}|COM\d{9}|EXP/\d{2}-\d{2}/\d{5})\b", re.I)
HS = re.compile(r"\b\d{8}(?:\d{2})?\b")
NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _decimal(raw: str) -> Decimal | None:
    try:
        return Decimal(raw.replace(",", ""))
    except (InvalidOperation, AttributeError):
        return None


def _valid_container(value: str) -> bool:
    """ISO 6346 check digit; excludes bank/account identifiers of similar shape."""
    alphabet = {ch: n for ch, n in zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        [10,12,13,14,15,16,17,18,19,20,21,23,24,25,26,27,28,29,30,31,32,34,35,36,37,38])}
    try:
        total = sum((alphabet.get(ch, int(ch) if ch.isdigit() else -999)) * (2 ** i)
                    for i, ch in enumerate(value[:10]))
        return total % 11 % 10 == int(value[10])
    except (ValueError, IndexError):
        return False


def _geometry(data: bytes) -> list[list[dict]]:
    # pdftotext exits nonzero for corrupt input and is bounded in time and size.
    proc = subprocess.run(["pdftotext", "-bbox-layout", "-", "-"], input=data,
                          capture_output=True, timeout=20, check=False)
    if proc.returncode or len(proc.stdout) > 30_000_000:
        return []
    root = ET.fromstring(proc.stdout)
    pages = []
    for page in root.iter():
        if page.tag.rsplit("}", 1)[-1] != "page":
            continue
        words = []
        for item in page.iter():
            if item.tag.rsplit("}", 1)[-1] != "word" or not item.text:
                continue
            words.append({"text": item.text, "bbox": [round(float(item.attrib[k]), 2)
                          for k in ("xMin", "yMin", "xMax", "yMax")]})
            if len(words) > WORD_LIMIT:
                raise ValueError("PDF_WORD_LIMIT_EXCEEDED")
        pages.append(words)
    return pages


def _locate(words: list[dict], raw: str) -> list[float] | None:
    """Return geometry only for a unique exact token sequence on one text line."""
    target = re.sub(r"[^A-Z0-9]", "", raw.upper())
    if not target: return None
    matches = []
    for i in range(len(words)):
        joined = ""
        first_y = words[i]["bbox"][1]
        for j in range(i, min(i + 40, len(words))):
            if abs(words[j]["bbox"][1] - first_y) > 4: break
            joined += re.sub(r"[^A-Z0-9]", "", words[j]["text"].upper())
            if joined == target:
                boxes = [w["bbox"] for w in words[i:j + 1]]
                matches.append([min(b[0] for b in boxes), min(b[1] for b in boxes),
                                max(b[2] for b in boxes), max(b[3] for b in boxes)])
                break
            if len(joined) > len(target): break
    return matches[0] if len(matches) == 1 else None


def _field(name: str, value: str, page: int, line: int, quote: str,
           words: list[dict]) -> dict:
    return {"field": name, "raw": value, "page": page, "line": line,
            "quote": quote, "bbox": _locate(words, value), "method": "pdf-text-rule"}


def extract_pdf_observations(data: bytes, filename: str) -> dict:
    start = time.perf_counter()
    result = {"filename": Path(filename).name, "sha256": hashlib.sha256(data).hexdigest(),
              "fields": [], "tables": [], "issues": [], "status": "REQUIRES_REVIEW"}
    if len(data) > MAX_BYTES:
        return {**result, "code": "FILE_TOO_LARGE", "processing_time_ms": 0}
    try:
        reader = PdfReader(io.BytesIO(data))
        result["pages"] = len(reader.pages)
        if len(reader.pages) > MAX_PAGES:
            return {**result, "code": "PDF_PAGE_LIMIT_EXCEEDED",
                    "processing_time_ms": round((time.perf_counter() - start) * 1000, 1)}
        geometry = _geometry(data)
        layout = subprocess.run(["pdftotext", "-layout", "-", "-"], input=data,
                                capture_output=True, timeout=20, check=False)
        if layout.returncode: raise ValueError("PDF_LAYOUT_FAILED")
        texts = [part.splitlines() for part in layout.stdout.decode("utf-8", "replace").split("\f")[:len(reader.pages)]]
    except (Exception,) as exc:
        return {**result, "code": "PDF_PARSE_FAILED", "reason": type(exc).__name__,
                "processing_time_ms": round((time.perf_counter() - start) * 1000, 1)}
    if not any(line.strip() for page in texts for line in page):
        result["issues"].append("PDF_OCR_REQUIRED")
    seen: set[tuple] = set()
    for p, lines in enumerate(texts, 1):
        words = geometry[p - 1] if p <= len(geometry) else []
        for n, line in enumerate(lines, 1):
            if "Country of Origin of goods" in line and n < len(lines):
                next_line = lines[n]
                match = re.search(r"\b(INDIA|CHINA|TURKEY)\s*$", next_line, re.I)
                if match and ("origin_country", match.group(1).upper()) not in seen:
                    result["fields"].append(_field("origin_country", match.group(1), p, n + 1, next_line, words))
                    seen.add(("origin_country", match.group(1).upper()))
            if "Country of Final Destination" in line and n < len(lines):
                next_line = lines[n]
                match = re.search(r"\b(UNITED STATES|ITALY|BELGIUM|NETHERLANDS)\s*$", next_line, re.I)
                if match and ("destination_country", match.group(1).upper()) not in seen:
                    result["fields"].append(_field("destination_country", match.group(1), p, n + 1, next_line, words))
                    seen.add(("destination_country", match.group(1).upper()))
            date_match = re.search(r"\bInvoice Date\s*:\s*(\d{2}-\d{2}-\d{4})\b", line, re.I)
            if date_match and ("invoice_date", date_match.group(1)) not in seen:
                result["fields"].append(_field("invoice_date", date_match.group(1), p, n, line, words))
                seen.add(("invoice_date", date_match.group(1)))
            for name, regex in (("invoice_number", INVOICE), ("container_number", CONTAINER)):
                for match in regex.finditer(line):
                    raw = match.group()
                    if name == "container_number" and not _valid_container(raw): continue
                    key = (name, raw.upper())
                    if key not in seen:
                        result["fields"].append(_field(name, raw, p, n, line, words)); seen.add(key)
            for name, pattern in (
                ("bill_of_lading", r"(?:MTD\s*/\s*BL\s*No|BILL OF LADING\s*[-:]?)\s*[:\-]?\s*([A-Z0-9]{8,20})"),
                ("purchase_order", r"(?:P\.?O\.?\s*(?:NUMBER|NO|#)?|PURCHASE ORDER)\s*[:#-]?\s*(\d{4,12})\b"),
                ("origin_country", r"Country of Origin of goods\s*[:\-]?\s*(INDIA|CHINA|[A-Z]{2})\b"),
                ("destination_country", r"Country of Final Destination\s*[:\-]?\s*(UNITED STATES|ITALY|BELGIUM|NETHERLANDS|[A-Z]{2})\b"),
            ):
                match = re.search(pattern, line, re.I)
                if match:
                    raw = match.group(1).strip()
                    if name == "bill_of_lading" and raw.upper() in {"CONTAINER", "SHIPPING", "NUMBER"}: continue
                    key = (name, raw.upper())
                    if key not in seen:
                        result["fields"].append(_field(name, raw, p, n, line, words)); seen.add(key)
            # A code is typed as HS only when explicitly labelled; item codes are excluded.
            match = re.search(r"\b(?:HSN?|RITC|CTH)\s*(?:CODE)?\s*[:#-]?\s*(\d{8}(?:\d{2})?)\b", line, re.I)
            if match:
                raw = match.group(1); key = ("hs_code", raw)
                if key not in seen:
                    result["fields"].append(_field("hs_code", raw, p, n, line, words)); seen.add(key)
            for name, pattern in (
                ("net_weight_kg", r"(?:Total\s+)?Net\s+W(?:eight|t)\s*(?:in\s*)?KGS?\s*[:]?\s*([\d,]+(?:\.\d+)?)"),
                ("gross_weight_kg", r"(?:Total\s+)?Gr(?:oss)?\s+W(?:eight|t)\s*(?:in\s*)?KGS?\s*[:]?\s*([\d,]+(?:\.\d+)?)"),
            ):
                match = re.search(pattern, line, re.I)
                if match:
                    raw = match.group(1); key = (name, raw)
                    if key not in seen:
                        result["fields"].append(_field(name, raw, p, n, line, words)); seen.add(key)
    # Layout-preserving text is only used to identify rows; page and geometry
    # remain sourced from the original PDF text/word layer.
    if layout.returncode == 0:
        for p, text in enumerate(layout.stdout.decode("utf-8", "replace").split("\f"), 1):
            if p > len(texts): break
            rows = []
            invoice_rows = []
            c1_rows = []
            page_words = geometry[p - 1] if p <= len(geometry) else []
            for raw in text.splitlines():
                inv = re.match(r"^\s*(.+?)\s{2,}(\d{8})\s+(\d+)\s+([\d,.]+)\s+([\d,.]+)\s*$", raw)
                if inv and "HSN CODE" in text and _decimal(inv.group(4)) and _decimal(inv.group(5)):
                    desc, hs, pcs, weight, value = inv.groups()
                    invoice_rows.append({"description": desc.strip(), "hs_code": hs,
                        "pieces": int(pcs), "net_weight_kg_raw": weight, "value_raw": value,
                        "currency": "USD" if "(USD)" in text else None,
                        "source": {"page": p, "bbox": _locate(page_words, hs), "quote": raw.strip()}})
                c1 = re.match(r"^\s*.+?\s+([A-Z]{4}\d{7})\s+\d{2}\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)\s*$", raw)
                if c1 and _valid_container(c1.group(1)) and "ANNEXURE" in text:
                    c1_rows.append({"container_number": c1.group(1), "packages": c1.group(2),
                        "gross_weight_kg_raw": c1.group(3), "net_weight_kg_raw": c1.group(4),
                        "source": {"page": p, "bbox": _locate(page_words, c1.group(1)), "quote": raw.strip()}})
                    result["fields"].append(_field("net_weight_kg", c1.group(4), p, 0, raw.strip(), page_words))
                    result["fields"].append(_field("gross_weight_kg", c1.group(3), p, 0, raw.strip(), page_words))
                match = re.match(r"^\s*(\d{1,3})\s+(\d{8,14})\s+(.+?)\s{2,}(\d+)\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)\s+(\d+)\s+(\d+)\s*$", raw)
                if not match: continue
                g = match.groups()
                if not all(_decimal(x) is not None for x in (g[3],g[4],g[5],g[6],g[7],g[8])): continue
                bbox = _locate(geometry[p - 1] if p <= len(geometry) else [], g[1])
                rows.append({"row_number": int(g[0]), "item_code": g[1], "description": g[2].strip(),
                             "pieces": int(g[3]), "unit_weight_kg_raw": g[4],
                             "net_weight_kg_raw": g[5], "gross_weight_kg_raw": g[6],
                             "per_crate_qty": int(g[7]), "crates": int(g[8]),
                             "source": {"page": p, "bbox": bbox, "quote": raw.strip()}})
            if rows:
                result["tables"].append({"kind": "packing_items", "page": p, "rows": rows})
            if invoice_rows:
                result["tables"].append({"kind": "invoice_items", "page": p, "rows": invoice_rows})
            if c1_rows:
                result["tables"].append({"kind": "customs_c1_containers", "page": p, "rows": c1_rows})
    result["processing_time_ms"] = round((time.perf_counter() - start) * 1000, 1)
    return result


def reconcile_documents(documents: list[dict]) -> dict:
    """Return only strongly supported same-shipment links and explicit conflicts."""
    groups = []
    for i, doc in enumerate(documents):
        obs = doc.get("observations") or {}
        fields = obs.get("fields") or []
        invoices = {f["raw"].upper() for f in fields if f["field"] == "invoice_number"}
        containers = {f["raw"].upper() for f in fields if f["field"] == "container_number"}
        groups.append((invoices, containers, fields))
    edges, conflicts = [], []
    for i in range(len(groups)):
        for j in range(i + 1, len(groups)):
            ai, ac, af = groups[i]; bi, bc, bf = groups[j]
            shared_invoices, shared_containers = ai & bi, ac & bc
            if not shared_invoices and not shared_containers: continue
            if ai and bi and not shared_invoices: continue
            if ac and bc and not shared_containers: continue
            if not shared_invoices: continue  # container alone may be reused
            edges.append({"from": i, "to": j, "invoice_numbers": sorted(shared_invoices),
                          "container_numbers": sorted(shared_containers), "status": "CANDIDATE_REQUIRES_REVIEW"})
            for name in ("net_weight_kg", "gross_weight_kg"):
                av = {_decimal(f["raw"]) for f in af if f["field"] == name}
                bv = {_decimal(f["raw"]) for f in bf if f["field"] == name}
                if av and bv and av.isdisjoint(bv):
                    conflicts.append({"documents": [i,j], "field": name,
                                      "left": sorted(str(x) for x in av), "right": sorted(str(x) for x in bv),
                                      "code": "SOURCE_VALUE_CONFLICT", "status": "BLOCKED_REQUIRES_RESOLUTION"})
    return {"edges": edges, "conflicts": conflicts,
            "status": "BLOCKED_REQUIRES_RESOLUTION" if conflicts else "REQUIRES_REVIEW"}


def invoice_candidates(observations: dict) -> list[dict]:
    """Review candidates only when a complete invoice item row is observed."""
    from .document_lines import _cells_to_line
    fields = observations.get("fields") or []
    def one(name):
        matches = [f for f in fields if f["field"] == name]
        return matches[0]["raw"] if len(matches) == 1 else None
    invoice = one("invoice_number")
    if not invoice: return []
    result = []
    for table in observations.get("tables") or []:
        if table["kind"] != "invoice_items": continue
        for i, row in enumerate(table["rows"], 1):
            headers = ["invoice_number", "cn_code", "quantity", "quantity_unit", "value", "currency",
                       "origin_country", "destination_country", "import_date", "container_number"]
            cells = [invoice, row["hs_code"], str(_decimal(row["net_weight_kg_raw"])), "KG",
                     str(_decimal(row["value_raw"])), row["currency"], one("origin_country"),
                     one("destination_country"), None, one("container_number")]
            candidate = _cells_to_line(cells, headers, filename=observations["filename"],
                                       sha256=observations["sha256"], row_number=i)
            for key in ("cn_code", "quantity", "value", "currency"):
                if key in candidate["field_provenance"]:
                    candidate["field_provenance"][key].update(row["source"])
                    candidate["field_provenance"][key]["method"] = "pdf-invoice-row"
            candidate["issues"].append("PDF_SOURCE_REQUIRES_REVIEW")
            result.append(candidate)
    return result
