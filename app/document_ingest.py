"""Document ingest for the workflow-run UI: parse uploads into redacted
shipment candidates + map each document to workflow steps + compare parsers.

Parser stack (per request):
- PDFs: PaddleOCR PP-StructureV3 (primary: layout + OCR + table/structure →
  markdown) vs pypdf (fast text layer) vs pdftotext baseline vs firecrawl
  (URL mode only, API-key gated). Comparison table shows chars/pages/time/CNs
  per parser; best pick = most CN hits, tie-break V3 > pypdf > baseline.
- CSV/XLSX: polars (read_csv / read_excel via calamine engine).
- TXT: direct decode.

Fail-closed: no guessing. Missing parsers, missing API keys, PII hits and
unparseable files return named codes, never silent passes. Raw uploads are
processed in-session only; only redacted candidates leave the parse step.
"""
from __future__ import annotations

import csv
import io
import os
import re
import subprocess
import tempfile
import time
from html.parser import HTMLParser

# --- PII patterns (preview redaction; matches tests/test_client_docs_use_case.py) ---
PII_PATTERNS = {
    "PAN": re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"),
    "GSTIN": re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z0-9][Zz][A-Z0-9]\b"),
    "IEC": re.compile(r"\bIEC[:\s]*\d{10}\b", re.IGNORECASE),
    "CIN": re.compile(r"\b[LU]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}\b"),
    "BANK_AC": re.compile(r"\b(?:account|a/c)[\s:]*\d{9,18}\b", re.IGNORECASE),
    "CONTAINER": re.compile(r"\b[A-Z]{4}\d{7}\b"),
}

CN_RE = re.compile(r"\b(\d{4})\s?(\d{2})\s?(\d{2})(?:\s?(\d{2}))?\b")
QTY_RE = re.compile(r"(\d[\d,]*\.?\d*)\s*(?:MT|M/T|TONNES?|TONS?|T)\b", re.IGNORECASE)
QTY_PREFIX_RE = re.compile(r"(?:qty|quantity|mass|weight|net_wt)[\s:]*(\d[\d,]*\.?\d*)", re.IGNORECASE)
EUR_RE = re.compile(r"(?:EUR|€)\s*([\d,]+\.?\d*)", re.IGNORECASE)
DATE_RE = re.compile(r"\b(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})\b|\b(\d{1,2})[-/.](\d{1,2})[-/.](20\d{2})\b")
ORIGIN_HINTS = ("INDIA", "IN ", " MUMBAI", "HAZIRA", "DADRI", "NHAVA", "MUNDRA")
DEST_HINTS = {
    "ANTWERP": "BE", "HAMBURG": "DE", "ROTTERDAM": "NL", "BUDAPEST": "HU",
    "GERMANY": "DE", "BELGIUM": "BE", "NETHERLANDS": "NL", "HUNGARY": "HU",
    "SPAIN": "ES", "ITALY": "IT", "FRANCE": "FR", "POLAND": "PL",
}


def redact_preview(text: str, limit: int = 2000) -> tuple[str, list[str]]:
    """Redact PII patterns in preview text. Returns (redacted, codes_hit)."""
    hits: list[str] = []
    out = text or ""
    for code, pat in PII_PATTERNS.items():
        if pat.search(out):
            hits.append(code)
            out = pat.sub(f"[REDACTED:{code}]", out)
    return out[:limit], hits


# --- PDF parsers ---

def parse_pdf_pypdf(data: bytes) -> dict:
    t0 = time.perf_counter()
    try:
        from pypdf import PdfReader
    except ImportError:
        return {"parser": "pypdf", "ok": False, "code": "PYPDF_NOT_INSTALLED",
                "reason": "pypdf is not installed in this environment."}
    try:
        reader = PdfReader(io.BytesIO(data))
        pages = len(reader.pages)
        chunks = []
        for p in reader.pages:
            try:
                chunks.append(p.extract_text() or "")
            except Exception:
                chunks.append("")
        text = "\n".join(chunks)
        ms = round((time.perf_counter() - t0) * 1000, 1)
        return {"parser": "pypdf", "ok": True, "pages": pages,
                "chars": len(text), "text": text, "time_ms": ms}
    except Exception as e:
        return {"parser": "pypdf", "ok": False, "code": "PYPDF_PARSE_FAILED",
                "reason": f"pypdf could not parse this file: {e}"}


def parse_pdf_baseline(data: bytes) -> dict:
    """pdftotext baseline (system binary). Kept so pypdf/firecrawl can be compared."""
    t0 = time.perf_counter()
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(data)
            path = f.name
        try:
            proc = subprocess.run(["pdftotext", "-layout", path, "-"],
                                  capture_output=True, timeout=60)
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass
        if proc.returncode != 0:
            return {"parser": "pdftotext-baseline", "ok": False,
                    "code": "PDFTOTEXT_FAILED",
                    "reason": (proc.stderr.decode(errors="replace")[:300]
                               or "pdftotext exited non-zero")}
        text = proc.stdout.decode(errors="replace")
        ms = round((time.perf_counter() - t0) * 1000, 1)
        return {"parser": "pdftotext-baseline", "ok": True,
                "pages": text.count("\f") + (1 if text.strip() else 0),
                "chars": len(text), "text": text, "time_ms": ms}
    except FileNotFoundError:
        return {"parser": "pdftotext-baseline", "ok": False,
                "code": "PDFTOTEXT_NOT_INSTALLED",
                "reason": "pdftotext system binary not found."}
    except subprocess.TimeoutExpired:
        return {"parser": "pdftotext-baseline", "ok": False,
                "code": "PDFTOTEXT_TIMEOUT", "reason": "pdftotext timed out."}


# --- PP-StructureV3 markdown post-processing ---
#
# paddlex emits tables as raw HTML blocks even from its "markdown" result,
# and, when a table's cell OCR comes back empty, as structure-only HTML with
# blank <td></td> cells (upstream table_recognition_post_processing falls
# back to space-joining the structure tokens). Downstream consumers want
# real markdown, so every <table> block is converted to a grid-aware pipe
# table (colspan/rowspan expanded) and tables with no text at all are
# dropped instead of shipped as empty HTML shells.

def _iter_table_spans(text: str):
    """Yield (start, end) spans of top-level <table>...</table> blocks."""
    depth = 0
    start = None
    for m in re.finditer(r"<table\b|</table>", text, flags=re.I):
        if m.group(0).startswith("</"):
            depth = max(0, depth - 1)
            if depth == 0 and start is not None:
                yield start, m.end()
                start = None
        else:
            if depth == 0:
                start = m.start()
            depth += 1


class _TableGridParser(HTMLParser):
    """Parse one HTML <table> block into rows of (text, colspan, rowspan)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[tuple[str, int, int]]] = []
        self._row: list[tuple[str, int, int]] | None = None
        self._cell: list[str] | None = None
        self._colspan = 1
        self._rowspan = 1

    @staticmethod
    def _span(value) -> int:
        try:
            return max(1, int(float(value)))
        except (TypeError, ValueError):
            return 1

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._close_row()
            self._row = []
        elif tag in ("td", "th"):
            self._close_cell()
            a = dict(attrs)
            self._colspan = self._span(a.get("colspan"))
            self._rowspan = self._span(a.get("rowspan"))
            self._cell = []
        elif self._cell is not None and tag in ("br", "p", "div"):
            self._cell.append(" ")

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)

    def _close_cell(self) -> None:
        if self._cell is None:
            return
        text = re.sub(r"\s+", " ", "".join(self._cell)).strip()
        if self._row is None:
            self._row = []
        self._row.append((text, self._colspan, self._rowspan))
        self._cell = None

    def _close_row(self) -> None:
        self._close_cell()
        if self._row:
            self.rows.append(self._row)
        self._row = None

    def handle_endtag(self, tag):
        if tag in ("td", "th"):
            self._close_cell()
        elif tag in ("tr", "table"):
            self._close_row()


def _take_pending(pending: dict[int, tuple[str, int]],
                  cells: dict[int, str]) -> None:
    """Materialise rowspan carries into this row and age them out."""
    for col in sorted(pending):
        text, left = pending[col]
        cells[col] = text
        if left <= 1:
            pending.pop(col)
        else:
            pending[col] = (text, left - 1)


def _table_grid(rows: list[list[tuple[str, int, int]]]) -> list[list[str]]:
    """Expand (text, colspan, rowspan) rows into a rectangular grid."""
    pending: dict[int, tuple[str, int]] = {}
    grid: list[list[str]] = []
    for row in rows:
        cells: dict[int, str] = {}
        _take_pending(pending, cells)
        for text, colspan, rowspan in row:
            col = 0
            while any((col + i) in cells for i in range(colspan)):
                col += 1
            for i in range(colspan):
                cells[col + i] = text if i == 0 else ""
                if rowspan > 1:
                    pending[col + i] = (text, rowspan - 1)
        grid.append([cells.get(c, "") for c in range(max(cells) + 1)]
                    if cells else [])
    while pending:
        cells = {}
        _take_pending(pending, cells)
        grid.append([cells.get(c, "") for c in range(max(cells) + 1)])
    if not grid:
        return []
    width = max(len(r) for r in grid)
    return [r + [""] * (width - len(r)) for r in grid]


def _table_html_to_markdown(table_html: str) -> str:
    """One <table> block → pipe-table markdown; '' when no cell has text."""
    parser = _TableGridParser()
    try:
        parser.feed(table_html)
        parser.close()
    except Exception:
        return ""
    grid = _table_grid(parser.rows)
    # Drop rows where every cell is empty: pure layout padding, lossless,
    # and keeps a blank first row from becoming the markdown header.
    grid = [row for row in grid if any(cell.strip() for cell in row)]
    if not grid:
        return ""

    def esc(cell: str) -> str:
        return cell.replace("|", "\\|").replace("\n", " ").strip()

    header = [esc(c) for c in grid[0]]
    body = [[esc(c) for c in row] for row in grid[1:]]
    width = len(header)
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(["---"] * width) + " |",
    ]
    for row in body:
        row = row + [""] * (width - len(row))
        lines.append("| " + " | ".join(row) + " |")
    return "\n" + "\n".join(lines) + "\n"


def html_tables_to_markdown(text: str) -> str:
    """Convert raw HTML table blocks in PP-StructureV3 output to markdown.

    - <table>...</table> → grid-aware pipe tables (colspan/rowspan expanded).
    - Tables whose cells are all empty (structure-only fallback) are dropped.
    - Leftover paddlex wrappers (<html>, <body>, <div style=...>) stripped.
    Text without table HTML passes through unchanged. Never raises.
    """
    text = text or ""
    if "<table" not in text.lower():
        return text
    parts: list[str] = []
    pos = 0
    for start, end in _iter_table_spans(text):
        parts.append(text[pos:start])
        parts.append(_table_html_to_markdown(text[start:end]))
        pos = end
    parts.append(text[pos:])
    out = "".join(parts)
    out = re.sub(r"</?(?:html|body)>", "", out, flags=re.I)
    out = re.sub(r"<div\b[^>]*>|</div>", "", out, flags=re.I)
    out = re.sub(r"[ \t]+\n", "\n", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    stripped = out.strip("\n")
    return stripped + "\n" if stripped else out


# Singleton PPStructureV3 pipeline (lazy: first call downloads models).
_PADDLE_V3_PIPELINE = None


def _paddle_device() -> str:
    """Resolve PP-StructureV3 device: EUROSETU_PADDLE_DEVICE override,
    else gpu:0 when torch sees a GPU, else cpu (fail-closed).

    PaddleX parse_device() only accepts paddle-style names
    (cpu/gpu/xpu/...), so cuda:0 is mapped to gpu:0 here.
    """
    forced = os.environ.get("EUROSETU_PADDLE_DEVICE", "").strip().lower()
    if forced in ("cuda", "cuda:0", "gpu", "gpu:0"):
        return "gpu:0"
    if forced:
        return forced
    try:
        import torch
        if torch.cuda.is_available():
            return "gpu:0"
    except Exception:
        pass
    return "cpu"


_PADDLEX_KMEANS_PATCHED = False

# Measured PP-StructureV3 throughput on the 35 client PDFs (GPU, RTX 3060):
# 1.56-5.43 s/page on typical docs, median 4.12, worst observed 36.12 (a
# dense table page). A flat 300 s cap therefore covers ~72 pages at median
# but only ~8 at worst-case density, and 6-page documents were being given
# the same 300 s as 120-page ones — the budget was both too generous on
# small files and too stingy on large dense ones.
_PADDLE_SEC_PER_PAGE = 4.12
_PADDLE_MIN_TIMEOUT_S = 120
_PADDLE_MAX_TIMEOUT_S = 900


def _pdf_page_count(data: bytes) -> int:
    """Page count, 1 when it cannot be determined (fail-closed to the floor)."""
    try:
        from pypdf import PdfReader
        return max(1, len(PdfReader(io.BytesIO(data)).pages))
    except Exception:
        return 1


def paddle_timeout_s(data: bytes) -> int:
    """Page-count-aware paddle budget, overridable via EUROSETU_PADDLE_TIMEOUT_S.

    A timeout is not a failure verdict: on a giant document the pypdf text
    layer usually wins anyway (243k chars, 5 CNs on the 348-page sample).
    This budget only decides when to stop waiting for the slow path.
    """
    forced = os.environ.get("EUROSETU_PADDLE_TIMEOUT_S", "").strip()
    if forced.isdigit() and int(forced) > 0:
        return int(forced)
    budget = int(_pdf_page_count(data) * _PADDLE_SEC_PER_PAGE * 3)  # 3x median headroom
    return max(_PADDLE_MIN_TIMEOUT_S, min(_PADDLE_MAX_TIMEOUT_S, budget))


def _release_gpu_cache() -> None:
    """Return freed VRAM to the OS after a parse.

    The paddle pipeline itself runs on the `transformers` engine, so the
    device memory is torch-owned — `paddle` is a CPU-only build here
    (paddle.device.is_compiled_with_cuda() is False) and its empty_cache is
    a no-op. torch's caching allocator keeps freed blocks reserved, which
    is what made the *second* large document in a batch OOM while the first
    had succeeded. Best-effort: never let cleanup mask the parse result.
    """
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass
    try:
        import paddle
        if paddle.device.is_compiled_with_cuda():
            paddle.device.cuda.empty_cache()
    except Exception:
        pass


# CUDA/torch OOM surfaces as an exception whose message names the allocator,
# not as a Python MemoryError. Same for CPU exhaustion. Matched
# case-insensitively on the phrases the allocators actually print.
# Deliberately NOT matched: pypdf's "cannot resize pool", which means the
# *file* is malformed and the user must replace the document.
_RESOURCE_FAILURE_RE = re.compile(
    r"out of memory|not enough memory|cuda error|bad_alloc|"
    r"resource[ _]?exhaust|cuda_failed_allocator|failed to allocate|"
    r"cuda_memory|defaultcpuallocator|cannot allocate memory",
    re.IGNORECASE,
)


def _is_resource_failure(exc: BaseException) -> bool:
    """True when a parse died from a device/memory limit, not a bad document.

    This distinction matters: "this PDF is malformed" is a document problem
    the user must fix, while "the GPU was full" is an environment problem we
    absorb by falling back to the text layer.
    """
    text = f"{type(exc).__name__}: {exc}"
    return bool(_RESOURCE_FAILURE_RE.search(text))


def _ensure_paddlex_kmeans_guard() -> None:
    """Patch upstream paddlex bug: table_recognition.combine_rectangles()
    passes N directly to sklearn KMeans(n_clusters=N). Pages with no
    predicted table cells reach it with N=0 → InvalidParameterError
    (sklearn requires n_clusters >= 1) → whole-file PADDLE_PARSE_FAILED.

    Upstream already returns unchanged rects when N >= num_rects; N <= 0
    must do the same. Idempotent, no-op if already patched or if the file
    layout changed (fail-closed: parse proceeds either way).
    """
    global _PADDLEX_KMEANS_PATCHED
    if _PADDLEX_KMEANS_PATCHED:
        return
    try:
        import importlib.util
        spec = importlib.util.find_spec(
            "paddlex.inference.pipelines.table_recognition.pipeline_v2")
        if spec is None or not spec.origin:
            return
        path = spec.origin
        with open(path, "r", encoding="utf-8") as f:
            src = f.read()
        old = "            if N >= num_rects:\n                return rectangles"
        new = ("            if N <= 0 or N >= num_rects:\n"
               "                return rectangles")
        if new in src or src.count(old) != 1:
            _PADDLEX_KMEANS_PATCHED = True
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(src.replace(old, new, 1))
        _PADDLEX_KMEANS_PATCHED = True
    except Exception:
        # Read-only site-packages etc: never block the parser.
        pass


def parse_pdf_paddle_structure(data: bytes, timeout_s: int | None = None) -> dict:
    """PP-StructureV3 path (primary): layout + OCR + tables → markdown text.

    Text detection uses PP-OCRv6_medium_det via the transformers engine
    (HF safetensors build PaddlePaddle/PP-OCRv6_medium_det_safetensors,
    ~88 MB) + PP-OCRv6_medium_rec for recognition. Writes bytes to a temp
    .pdf, runs the singleton PPStructureV3 pipeline, concatenates per-page
    markdown via pipeline.concatenate_markdown_pages. Fail-closed with
    named codes; never raises. First call downloads models and is slow;
    later calls reuse the singleton.
    """
    t0 = time.perf_counter()
    timeout_s = paddle_timeout_s(data) if timeout_s is None else timeout_s
    try:
        from paddleocr import PPStructureV3
    except ImportError:
        return {"parser": "paddle-structure-v3", "ok": False,
                "code": "PADDLE_NOT_INSTALLED",
                "reason": "paddleocr is not installed (needs paddleocr + paddlepaddle)."}
    global _PADDLE_V3_PIPELINE
    try:
        _ensure_paddlex_kmeans_guard()
        if _PADDLE_V3_PIPELINE is None:
            device = _paddle_device()
            try:
                _PADDLE_V3_PIPELINE = PPStructureV3(
                    lang="en",
                    engine="transformers",
                    device=device,
                    text_detection_model_name="PP-OCRv6_medium_det",
                    text_recognition_model_name="PP-OCRv6_medium_rec",
                )
            except Exception:
                if device == "cpu":
                    raise
                # GPU init failed → fall back to CPU rather than lose the parser.
                _PADDLE_V3_PIPELINE = PPStructureV3(
                    lang="en",
                    engine="transformers",
                    device="cpu",
                    text_detection_model_name="PP-OCRv6_medium_det",
                    text_recognition_model_name="PP-OCRv6_medium_rec",
                )
        pipeline = _PADDLE_V3_PIPELINE
    except Exception as e:
        return {"parser": "paddle-structure-v3", "ok": False,
                "code": "PADDLE_INIT_FAILED",
                "reason": f"Could not initialise PPStructureV3: {e}"}
    path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(data)
            path = f.name
        # NOTE: deliberately NOT `with ThreadPoolExecutor(...)`. __exit__ calls
        # shutdown(wait=True), so returning from inside the with-block after a
        # timeout still blocks until the worker finishes — a "300 s" timeout
        # then costs however long the parse really takes. On timeout we
        # shutdown(wait=False) and return immediately; the abandoned worker
        # keeps burning GPU/CPU in the background but cannot block the
        # request. On success we join, so the thread is reaped cleanly.
        import concurrent.futures
        ex = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        fut = ex.submit(_paddle_v3_predict, pipeline, path)
        try:
            markdown_texts, pages = fut.result(timeout=timeout_s)
        except concurrent.futures.TimeoutError:
            ex.shutdown(wait=False)
            # Not a document error: the heavy path ran out of patience on a
            # large file. Callers treat this as "fallback parser won", so it is
            # flagged advisory rather than as a failed parse. Release the
            # allocator cache too — the abandoned worker is still holding it.
            _release_gpu_cache()
            return {"parser": "paddle-structure-v3", "ok": False,
                    "code": "PADDLE_TIMEOUT", "advisory": True,
                    "reason": f"PP-StructureV3 exceeded {timeout_s}s on this file - the text-layer parser is used instead."}
        except Exception:
            ex.shutdown(wait=False)
            raise
        else:
            ex.shutdown(wait=True)
        ms = round((time.perf_counter() - t0) * 1000, 1)
        markdown_texts = str(markdown_texts or "")
        # paddlex "markdown" still contains raw HTML table blocks; convert
        # to pipe tables and drop empty ones so output is true markdown.
        markdown_texts = html_tables_to_markdown(markdown_texts)
        # Hand the reserved blocks back so the next document in a batch starts
        # from a clean allocator instead of inheriting this one's peak.
        _release_gpu_cache()
        return {"parser": "paddle-structure-v3", "ok": True, "pages": pages,
                "chars": len(markdown_texts), "text": markdown_texts, "time_ms": ms}
    except Exception as e:
        # A device/memory limit is an environment problem, not a bad
        # document. Classify it as advisory so callers (and the UI) show a
        # neutral FALLBACK row and the pypdf/pdftotext text layer wins,
        # instead of a red failure on a document we can still read.
        if _is_resource_failure(e):
            return {"parser": "paddle-structure-v3", "ok": False,
                    "code": "PADDLE_RESOURCE_EXHAUSTED", "advisory": True,
                    "reason": (f"PP-StructureV3 hit a device/memory limit "
                               f"({type(e).__name__}); the text-layer parser is "
                               f"used instead.")}
        return {"parser": "paddle-structure-v3", "ok": False,
                "code": "PADDLE_PARSE_FAILED",
                "reason": f"PP-StructureV3 could not parse this file: {e}"}
    finally:
        if path:
            try:
                os.unlink(path)
            except OSError:
                pass


# Predict-time options for PP-StructureV3. The default e2e wireless table
# model falls back to structure-only HTML with entirely empty cells when its
# cell OCR yields nothing (verified: 0/28 cells populated on
# scribd-903558901). The non-e2e path runs cell detection + per-cell OCR
# instead (13/28 populated on the same file, 156/201 vs 144/201 on a
# populated control) — so the e2e wireless model is disabled here.
_PADDLE_PREDICT_KWARGS = {
    "use_e2e_wireless_table_rec_model": False,
}


def _paddle_v3_predict(pipeline, path: str) -> tuple[str, int]:
    try:
        output = pipeline.predict(input=path, **_PADDLE_PREDICT_KWARGS)
    except TypeError:
        # Older paddleocr without these kwargs: fail closed to defaults.
        output = pipeline.predict(input=path)
    markdown_list = []
    for res in output:
        md_info = res.markdown
        if isinstance(md_info, dict):
            markdown_list.append(md_info)
        elif hasattr(md_info, "get"):
            try:
                markdown_list.append({"markdown_texts": md_info.get("markdown_texts", "") or str(md_info)})
            except Exception:
                markdown_list.append({"markdown_texts": str(md_info or "")})
        else:
            markdown_list.append({"markdown_texts": str(md_info or "")})
    try:
        concat = pipeline.concatenate_markdown_pages(markdown_list)
        # paddlex returns a MarkdownResult (dict-like) holding "markdown_texts".
        if isinstance(concat, dict) or hasattr(concat, "get"):
            try:
                text = concat.get("markdown_texts", "") or ""
            except Exception:
                text = str(concat or "")
        elif isinstance(concat, (tuple, list)):
            first = concat[0] if concat else ""
            if isinstance(first, dict) or hasattr(first, "get"):
                try:
                    text = first.get("markdown_texts", "") or ""
                except Exception:
                    text = str(first or "")
            else:
                text = first or ""
        else:
            text = concat or ""
        text = str(text)
    except Exception:
        text = "\n".join(str(m.get("markdown_texts", "")) for m in markdown_list)
    return text, len(markdown_list)


def parse_pdf_firecrawl_url(url: str) -> dict:
    """Firecrawl path: URL mode only (local bytes have no hosted URL).

    Gated on FIRECRAWL_API_KEY. Fail-closed with named codes otherwise.
    """
    t0 = time.perf_counter()
    key = (os.getenv("FIRECRAWL_API_KEY") or "").strip()
    if not key:
        return {"parser": "firecrawl", "ok": False, "code": "FIRECRAWL_API_KEY_MISSING",
                "reason": "Set FIRECRAWL_API_KEY to enable the firecrawl comparison path."}
    if not url:
        return {"parser": "firecrawl", "ok": False, "code": "FIRECRAWL_NEEDS_HOSTED_URL",
                "reason": "Firecrawl parses hosted URLs, not raw upload bytes. Paste a document URL to compare."}
    try:
        from firecrawl import FirecrawlApp
    except ImportError:
        return {"parser": "firecrawl", "ok": False, "code": "FIRECRAWL_NOT_INSTALLED",
                "reason": "firecrawl-py is not installed."}
    try:
        app = FirecrawlApp(api_key=key)
        doc = app.scrape_url(url, params={"formats": ["markdown", "text"]})
        text = (getattr(doc, "markdown", "") or "") + "\n" + (getattr(doc, "text", "") or "")
        if isinstance(doc, dict):
            text = (doc.get("markdown") or "") + "\n" + (doc.get("text") or "")
        ms = round((time.perf_counter() - t0) * 1000, 1)
        return {"parser": "firecrawl", "ok": True, "pages": 1,
                "chars": len(text), "text": text, "time_ms": ms}
    except Exception as e:
        return {"parser": "firecrawl", "ok": False, "code": "FIRECRAWL_REQUEST_FAILED",
                "reason": f"Firecrawl request failed: {e}"}


# --- Tabular parsers (polars) ---

def parse_csv_polars(data: bytes) -> dict:
    t0 = time.perf_counter()
    try:
        import polars as pl
    except ImportError:
        return {"parser": "polars-csv", "ok": False, "code": "POLARS_NOT_INSTALLED",
                "reason": "polars is not installed."}
    try:
        df = pl.read_csv(io.BytesIO(data), infer_schema_length=1000,
                         truncate_ragged_lines=True)
        ms = round((time.perf_counter() - t0) * 1000, 1)
        return {"parser": "polars-csv", "ok": True, "rows": df.height,
                "columns": list(df.columns), "frame": df,
                "text": df.head(50).write_csv(), "time_ms": ms}
    except Exception as e:
        return {"parser": "polars-csv", "ok": False, "code": "CSV_PARSE_FAILED",
                "reason": f"polars could not parse this CSV: {e}"}


def parse_excel_polars(data: bytes) -> dict:
    t0 = time.perf_counter()
    try:
        import polars as pl
    except ImportError:
        return {"parser": "polars-excel", "ok": False, "code": "POLARS_NOT_INSTALLED",
                "reason": "polars is not installed."}
    try:
        xls = None
        last_err = None
        for engine in ("calamine", "openpyxl"):
            try:
                xls = pl.read_excel(io.BytesIO(data), sheet_id=0, engine=engine)
                break
            except Exception as e:
                last_err = e
                continue
        if xls is None:
            raise last_err or RuntimeError("no Excel engine available")
        if isinstance(xls, dict):
            # multiple sheets: keep first non-empty, report names
            names = list(xls.keys())
            df = next((d for d in xls.values() if d.height), next(iter(xls.values())))
        else:
            names, df = (["Sheet1"], xls)
        ms = round((time.perf_counter() - t0) * 1000, 1)
        return {"parser": "polars-excel", "ok": True, "rows": df.height,
                "columns": list(df.columns), "sheets": names, "frame": df,
                "text": df.head(50).write_csv(), "time_ms": ms}
    except Exception as e:
        return {"parser": "polars-excel", "ok": False, "code": "EXCEL_PARSE_FAILED",
                "reason": f"polars could not parse this workbook: {e}"}


def parse_txt(data: bytes) -> dict:
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            text = data.decode(enc)
            return {"parser": "text", "ok": True, "pages": 1,
                    "chars": len(text), "text": text, "time_ms": 0.0}
        except (UnicodeDecodeError, ValueError):
            continue
    return {"parser": "text", "ok": False, "code": "TEXT_DECODE_FAILED",
            "reason": "Could not decode as utf-8 or latin-1."}


# --- Extraction → redacted candidate ---

def extract_candidates(text: str, source_name: str) -> dict:
    """Regex-extract CN/qty/value/date/route hints. Never invents; missing → None."""
    cns = []
    for m in CN_RE.finditer(text or ""):
        digits = re.sub(r"\s", "", m.group(0))
        if len(digits) >= 8 and digits not in cns:
            cns.append(digits[:8])
    qtys = [float(q.replace(",", "")) for q in QTY_RE.findall(text or "")]
    qtys += [float(q.replace(",", "")) for q in QTY_PREFIX_RE.findall(text or "")
             if float(q.replace(",", "")) not in qtys]
    vals = [float(v.replace(",", "")) for v in EUR_RE.findall(text or "")]
    dates = []
    for m in DATE_RE.finditer(text or ""):
        dates.append(m.group(0))
    upper = (text or "").upper()
    origin = "IN" if any(h in upper for h in ORIGIN_HINTS) else None
    dest = None
    for hint, code in DEST_HINTS.items():
        if hint in upper:
            dest = code
            break
    return {
        "source": source_name,
        "cn_codes_found": cns[:10],
        "quantities_t_found": qtys[:10],
        "values_eur_found": vals[:10],
        "dates_found": dates[:10],
        "origin_hint": origin,
        "destination_hint": dest,
        "candidate": {
            "cn_code": cns[0] if cns else None,
            "quantity_t": max(qtys) if qtys else None,
            "customs_value_eur": max(vals) if vals else None,
            "origin_country": origin,
            "import_date": None,  # user confirms; never guessed from mixed hits
        },
    }


# --- Receipt records (typed, fail-closed) ---
#
# Receipts (CORD / SAP MM material receipts) need one typed record per row -
# receipt id, vendor, total, qty - instead of one shipment candidate. Each
# cell keeps its raw string, a parsed number (None when ambiguous) and a
# named code, mirroring the defect shapes in use_cases/ouco_mtc_messy/
# receipts_messy_sample.csv:
#   decimal_comma   "1,9"     -> RECEIPT_TOTAL_DECIMAL_COMMA (never 19)
#   units_embedded  "412 EUR" -> RECEIPT_TOTAL_UNITS_EMBEDDED
#   qty mismatch    "2 vs 3"  -> RECEIPT_QTY_UNPARSEABLE
#   duplicate repost          -> RECEIPT_DUPLICATE + duplicate_of pointer
# Dedupe key = "<sha16 or source>:<row index>". String fields run through
# the same PII patterns as redact_preview - only redacted records leave the
# parse step. Reads pipe tables (paddle markdown) and CSV blocks alike.

_RECEIPT_UNITS_RE = re.compile(
    r"(?i)(?<![a-z])(?:eur|usd|inr|gbp|rs|kg|kgs|mt|tons?|tonnes?|pcs|units?)(?![a-z])")
_RECEIPT_SEP_RE = re.compile(r":?-{2,}:?")


def _receipt_header_map(cells: list) -> dict | None:
    """Field -> column index for receipt-shaped headers. Requires a
    receipt-id or vendor column so quantity/amount-only tables (CN lines)
    are left to extract_candidates instead of being read as receipts."""
    norm = {i: re.sub(r"[^a-z0-9]", "", str(c or "").lower())
            for i, c in enumerate(cells)}
    out: dict = {}

    def take(field: str, pred) -> None:
        if field in out:
            return
        for i, key in norm.items():
            if key and pred(key):
                out[field] = i
                return

    take("receipt_id", lambda k: k.startswith("receipt") or k.startswith("rcpt")
         or k in {"id", "invoiceno", "invoice", "ref", "reference",
                  "docno", "documentno", "orderno", "mrn"})
    take("vendor", lambda k: k in {"vendor", "vendorname", "supplier",
                                   "suppliername", "seller", "merchant",
                                   "party", "counterparty", "from"})
    take("total", lambda k: k.startswith("total") or k in {"amount",
         "amounteur", "totaleur", "valueeur", "price", "gross", "sum",
         "totalamount", "lineamount", "nettotal"})
    take("qty", lambda k: k.startswith("qty") or k.startswith("quant")
         or k in {"quantity", "units", "count", "mass", "weight", "netwt"})
    take("date", lambda k: k.endswith("date") or k in {"issued", "timestamp", "dtd"})
    if "receipt_id" not in out and "vendor" not in out:
        return None
    return out


def _receipt_pipe_blocks(text: str):
    """Consecutive '| ... |' lines as row lists (escaped \\| kept in-cell)."""
    block: list = []
    for line in (text or "").splitlines():
        s = line.strip()
        if len(s) >= 2 and s.startswith("|") and s.endswith("|"):
            inner = s[1:-1].replace("\\|", "\x00")
            block.append([c.strip().replace("\x00", "|") for c in inner.split("|")])
        elif block:
            yield block
            block = []
    if block:
        yield block


def _receipt_csv_blocks(text: str):
    """Consecutive comma-lines (CSV export / pasted ledger) as row lists."""
    block: list = []
    for line in list((text or "").splitlines()) + [""]:
        s = line.strip()
        if s and "," in s and not s.startswith("|"):
            block.append(line)
        elif block:
            yield block
            block = []


def _receipt_tables(text: str):
    """Receipt-shaped tables. A single header row is still a real table
    (zero data rows), so blocks are yielded as-is and the header map is the
    gate: a quantity/amount-only table is not a receipt table."""
    for block in _receipt_pipe_blocks(text):
        yield block
    for block in _receipt_csv_blocks(text):
        try:
            rows = [r for r in csv.reader(block)]
        except csv.Error:
            continue
        if rows:
            yield rows


def _receipt_number(raw, field: str) -> tuple:
    """(value, code) - value is None whenever the raw cell is ambiguous."""
    s = str(raw or "").strip()
    if not s:
        return None, f"RECEIPT_{field}_MISSING"
    if re.fullmatch(r"-?\d+(?:\.\d+)?", s):
        return float(s), None
    if "," in s:
        # "1,9" must never become 19; "1,900" could be 1.900 or 1900.
        return None, f"RECEIPT_{field}_DECIMAL_COMMA"
    if _RECEIPT_UNITS_RE.search(s) or any(ch in s for ch in "€$\u00a5"):
        return None, f"RECEIPT_{field}_UNITS_EMBEDDED"
    return None, f"RECEIPT_{field}_UNPARSEABLE"


def _receipt_redact(value):
    out = str(value or "")
    for code, pat in PII_PATTERNS.items():
        out = pat.sub(f"[REDACTED:{code}]", out)
    return out or None


def extract_receipt_records(text: str, source_name: str,
                            sha16: str = "") -> dict:
    """Typed receipt records from pipe/CSV tables in `text` (fail-closed).

    Returns {source, sha16, rows, records, codes}: one record per row with
    record_key "<sha16 or source>:<row>", raw + parsed fields, per-row codes
    and duplicate_of pointers; top-level codes = NO_RECEIPT_TABLE /
    NO_RECEIPT_ROWS when nothing usable was found. Never invents numbers.
    """
    prefix = sha16 or source_name or "doc"
    records: list = []
    seen: dict = {}
    row_index = 0
    tables = 0
    for rows in _receipt_tables(text or ""):
        mapping = _receipt_header_map(rows[0])
        if not mapping:
            continue
        tables += 1
        header = [str(c) for c in rows[0]]
        for cells in rows[1:]:
            cells = [str(c or "") for c in cells]
            if not any(c.strip() for c in cells):
                continue
            if all(_RECEIPT_SEP_RE.fullmatch(c.strip())
                   for c in cells if c.strip()):
                continue
            g = lambda f: (cells[mapping[f]].strip()
                           if f in mapping and mapping[f] < len(cells) else "")
            total, code_total = _receipt_number(g("total"), "TOTAL")
            if "qty" in mapping:
                quantity, code_qty = _receipt_number(g("qty"), "QTY")
            else:
                quantity, code_qty = None, None
            receipt_id = _receipt_redact(g("receipt_id"))
            vendor = _receipt_redact(g("vendor"))
            date = _receipt_redact(g("date"))
            codes = [c for c in (code_total, code_qty) if c]
            identity = (receipt_id or "").strip().upper()
            if not identity:
                identity = "|".join(s.strip() for s in
                                    (vendor or "", g("total"), g("qty")))
            key = f"{prefix}:{row_index}"
            duplicate_of = None
            if identity.strip("| "):
                if identity in seen:
                    codes.append("RECEIPT_DUPLICATE")
                    duplicate_of = seen[identity]
                else:
                    seen[identity] = key
            extra = {header[i]: _receipt_redact(cells[i])
                     for i in range(min(len(header), len(cells)))
                     if i not in mapping.values() and cells[i].strip()}
            records.append({
                "record_key": key,
                "receipt_id": receipt_id,
                "vendor": vendor,
                "total_raw": g("total") or None,
                "total": total,
                "qty_raw": g("qty") or None,
                "quantity": quantity,
                "date": date,
                "extra": extra,
                "codes": codes,
                "duplicate_of": duplicate_of,
            })
            row_index += 1
    codes = []
    if tables == 0:
        codes.append("NO_RECEIPT_TABLE")
    elif not records:
        codes.append("NO_RECEIPT_ROWS")
    return {"source": source_name, "sha16": sha16, "rows": len(records),
            "records": records, "codes": codes}


def dataframe_candidates(df, source_name: str) -> dict:
    """Map polars frame columns onto candidate fields by header name."""
    try:
        cols = {str(c).lower().strip(): str(c) for c in df.columns}
    except Exception:
        return {"source": source_name, "rows": 0, "candidates": [],
                "code": "FRAME_UNREADABLE", "reason": "Could not read columns."}

    def col(*names):
        for n in names:
            if n in cols:
                return cols[n]
        return None

    c_cn = col("cn_code", "cn", "commodity", "hs_code", "taric")
    c_qty = col("quantity_t", "qty", "mass_t", "mass", "quantity", "tonnes", "net_mass")
    c_val = col("customs_value_eur", "value_eur", "value", "line_value_eur", "amount_eur")
    c_org = col("origin_country", "origin", "country")
    c_date = col("import_date", "shipment_date", "date")
    c_ref = col("shipment_ref", "transaction_id", "ref", "mrn", "po_number")
    out = []
    try:
        for i, row in enumerate(df.iter_rows(named=True)):
            if i >= 200:
                break
            g = lambda k: row.get(k) if k else None  # noqa: E731
            cn = g(c_cn)
            cn_digits = re.sub(r"\D", "", str(cn or ""))
            out.append({
                "shipment_ref": str(g(c_ref) or f"{source_name}-ROW-{i + 1}"),
                "cn_code": cn_digits[:8] or None,
                "quantity_t": _num(g(c_qty)),
                "customs_value_eur": _num(g(c_val)),
                "origin_country": (str(g(c_org) or "IN").upper()[:2]),
                "import_date": str(g(c_date) or "") or None,
            })
    except Exception as e:
        return {"source": source_name, "code": "FRAME_ROW_FAILED",
                "reason": f"Row mapping failed: {e}", "candidates": []}
    return {"source": source_name, "rows": len(out), "candidates": out,
            "mapped_columns": {"cn": c_cn, "qty": c_qty, "value": c_val,
                               "origin": c_org, "date": c_date, "ref": c_ref}}


def _num(v) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(str(v).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


# --- Doc → workflow-step mapping ---

def map_to_steps(filename: str, extracted: dict) -> dict:
    """State what each document contributes to each workflow step.

    Step 1 (compile obligations): commercial docs → CN/origin/value/qty/TARIC scope.
    Step 2 (trace evidence): certs/supplier/verifier docs → evidence state.
    Step 3 (price/prioritise/pack): everything resolved → READY/BLOCKED + blockers.
    """
    name = (filename or "").lower()
    step1, step2 = [], []
    if any(k in name for k in ("invoice", "packing", "sb ", "sb_", "shipping", "bill", "ledger", "csv", "xls")):
        step1.append("CN code + quantity + customs value + origin → TARIC/CBAM/steel scope gate")
    if any(k in name for k in ("mtc", "mill", "test", "certificate", "en10204", "inspection")):
        step2.append("Mill/test certificate → material evidence (UNVERIFIED until verifier confirms)")
    if any(k in name for k in ("supplier", "emission", "cbam", "monitoring", "verifier", "verification")):
        step2.append("Supplier emissions / verifier statement → CBAM evidence (VALID only when VERIFIED)")
    if any(k in name for k in ("quota", "taric", "customs", "declaration")):
        step1.append("Customs/quota reference → duty + safeguard treatment inputs")
    if not step1 and not step2:
        step1.append("Free-text facts → candidate CN/qty/value/route for user confirmation")
    step3 = ["Resolved lines price per Step 1 scope + Step 2 evidence → READY_FOR_SUBMISSION or BLOCKED with named blockers"]
    if extracted.get("cn_codes_found"):
        step1.append(f"Found CN hint(s): {', '.join(extracted['cn_codes_found'][:3])} (confirm before compiling)")
    return {"step_1_compile_obligations": step1,
            "step_2_trace_evidence": step2,
            "step_3_price_prioritise_pack": step3}


def compare_pdf_parsers(data: bytes, include_paddle: bool = True) -> list[dict]:
    """Run paddle-structure-v3 + pypdf + pdftotext baseline; firecrawl stays URL-mode.

    V3 is the primary (layout + OCR + tables → markdown); pypdf/baseline are
    fast text-layer fallbacks. Set include_paddle=False to skip the heavy
    model path (first call downloads models). Keeps full text on each row
    under "text" so the caller can pick the best parse; the caller strips
    "text" before returning rows to the browser.
    """
    rows = []
    if include_paddle:
        rows.append(parse_pdf_paddle_structure(data))
    rows += [parse_pdf_pypdf(data), parse_pdf_baseline(data)]
    rows.append({"parser": "firecrawl", "ok": False,
                 "advisory": True,
                 "code": "FIRECRAWL_NEEDS_HOSTED_URL",
                 "reason": "Firecrawl parses hosted URLs (needs FIRECRAWL_API_KEY + URL); uploads compare V3 vs pypdf vs pdftotext."})
    for r in rows:
        raw = r.get("text", "")
        if isinstance(raw, dict) or hasattr(raw, "get"):
            try:
                raw = raw.get("markdown_texts", "") or ""
            except Exception:
                raw = str(raw or "")
        txt = str(raw or "")
        r["text"] = txt
        r["cns_found"] = [re.sub(r"\s", "", m.group(0))[:8]
                          for m in list(CN_RE.finditer(txt))[:5]]
        r["chars"] = r.get("chars", len(txt)) if isinstance(r.get("chars"), int) else len(txt)
    return rows
