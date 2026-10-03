"""Tests for the PP-StructureV3 timeout budget and advisory classification.

The point of these: a timeout on a giant PDF is a FALLBACK, not a document
error. pypdf returns 243k chars / 5 CNs on the 348-page sample, so painting
PADDLE_TIMEOUT as a red failure misrepresents a perfectly healthy parse.
"""

import time

import pytest

from app import document_ingest as ing


# --- budget sizing -------------------------------------------------------

def test_tiny_doc_gets_the_floor(monkeypatch):
    monkeypatch.setattr(ing, "_pdf_page_count", lambda _d: 2)
    assert ing.paddle_timeout_s(b"x") == ing._PADDLE_MIN_TIMEOUT_S


def test_budget_scales_with_page_count(monkeypatch):
    monkeypatch.setenv("EUROSETU_PADDLE_TIMEOUT_S", "")
    monkeypatch.setattr(ing, "_pdf_page_count", lambda _d: 50)
    assert ing.paddle_timeout_s(b"x") > ing._PADDLE_MIN_TIMEOUT_S


def test_giant_doc_is_capped_not_unbounded(monkeypatch):
    """A 5000-page doc must not get an unbounded budget — the cap is what
    stops one upload from pinning a worker forever."""
    monkeypatch.setenv("EUROSETU_PADDLE_TIMEOUT_S", "")
    monkeypatch.setattr(ing, "_pdf_page_count", lambda _d: 5000)
    assert ing.paddle_timeout_s(b"x") == ing._PADDLE_MAX_TIMEOUT_S


def test_env_override_wins(monkeypatch):
    monkeypatch.setenv("EUROSETU_PADDLE_TIMEOUT_S", "45")
    monkeypatch.setattr(ing, "_pdf_page_count", lambda _d: 5000)
    assert ing.paddle_timeout_s(b"x") == 45


def test_junk_env_override_is_ignored(monkeypatch):
    monkeypatch.setenv("EUROSETU_PADDLE_TIMEOUT_S", "junk")
    monkeypatch.setattr(ing, "_pdf_page_count", lambda _d: 2)
    assert ing.paddle_timeout_s(b"x") == ing._PADDLE_MIN_TIMEOUT_S


def test_unreadable_pdf_fails_closed_to_floor():
    """Garbage bytes must not crash or produce a zero/negative budget."""
    assert ing.paddle_timeout_s(b"not a pdf at all") == ing._PADDLE_MIN_TIMEOUT_S


def test_page_count_of_garbage_is_one():
    assert ing._pdf_page_count(b"not a pdf at all") == 1


# --- advisory classification --------------------------------------------

def test_timeout_is_advisory_not_a_failure(monkeypatch):
    """PADDLE_TIMEOUT must be flagged advisory so callers/UI treat it as
    'fallback parser won' rather than 'document failed'."""
    rows = []
    for r in ing.compare_pdf_parsers(b"%PDF-1.4 broken", include_paddle=False):
        rows.append(r)
    for r in rows:
        if r["parser"] == "firecrawl":
            assert r["advisory"] is True


def _timeout_row() -> dict:
    """Drive a real (fast) timeout and return the row the parser produced."""
    try:
        import paddleocr  # noqa: F401
    except ImportError:
        pytest.skip("paddleocr not installed")

    class _Pipe:
        pass

    orig_pipe, orig_predict = ing._PADDLE_V3_PIPELINE, ing._paddle_v3_predict
    try:
        ing._PADDLE_V3_PIPELINE = _Pipe()
        ing._paddle_v3_predict = lambda *a, **k: time.sleep(2)
        return ing.parse_pdf_paddle_structure(b"%PDF-1.4 fake", timeout_s=0)
    finally:
        ing._PADDLE_V3_PIPELINE = orig_pipe
        ing._paddle_v3_predict = orig_predict


def test_timeout_row_is_advisory():
    res = _timeout_row()
    assert res["ok"] is False
    assert res["code"] == "PADDLE_TIMEOUT"
    assert res["advisory"] is True
    # and it must say the fallback is in use, not just that it ran out of time
    assert "instead" in res["reason"]


def test_firecrawl_row_is_advisory():
    rows = ing.compare_pdf_parsers(b"%PDF-1.4 broken", include_paddle=False)
    fc = next(r for r in rows if r["parser"] == "firecrawl")
    assert fc["ok"] is False
    assert fc["advisory"] is True


def test_hard_failures_are_not_advisory():
    """A genuinely broken document must NOT be softened into 'advisory'."""
    rows = ing.compare_pdf_parsers(b"%PDF-1.4 broken", include_paddle=False)
    for r in rows:
        if r["parser"] == "firecrawl":
            continue
        assert r.get("ok") is False
        assert r.get("advisory") is not True


# --- timeout is actually enforced ---------------------------------------

def test_timeout_returns_without_waiting_for_the_worker(monkeypatch):
    """The regression: `with ThreadPoolExecutor(...)` calls shutdown(wait=True),
    so returning from inside the with-block after a timeout STILL blocks until
    the worker finishes. A 1s budget on a 6s job must return immediately.

    `paddleocr` is imported before t0 on every call (7.4 s cold), so warm it
    first — otherwise the test measures import time, not the timeout.
    """
    try:
        import paddleocr  # noqa: F401
    except ImportError:
        pytest.skip("paddleocr not installed")

    monkeypatch.setattr(ing, "_PADDLE_V3_PIPELINE", object())
    monkeypatch.setattr(ing, "_paddle_v3_predict",
                        lambda *a, **k: (time.sleep(6), ("", 0))[1])

    t0 = time.perf_counter()
    res = ing.parse_pdf_paddle_structure(b"%PDF-1.4 fake", timeout_s=1)
    elapsed = time.perf_counter() - t0

    assert res["ok"] is False
    assert res["code"] == "PADDLE_TIMEOUT"
    assert res["advisory"] is True
    assert elapsed < 3.0, f"timeout not enforced: took {elapsed:.1f}s"


# --- resource exhaustion is advisory, document errors are not -----------

class _FakeOOM(RuntimeError):
    pass


@pytest.mark.parametrize("msg", [
    "CUDA out of memory. Tried to allocate 2.00 GiB",
    "DefaultCPUAllocator: not enough memory: you tried to allocate",
    "CUDA failed to allocate 165675008 bytes",
    "resource exhausted: cuda",
])
def test_device_memory_failures_are_resource_failures(msg):
    assert ing._is_resource_failure(RuntimeError(msg)) is True


@pytest.mark.parametrize("msg", [
    "Invalid PDF structure",
    "EOF marker not found",
    "cannot resize pool",
    "unable to write file",
])
def test_document_errors_are_not_resource_failures(msg):
    """A malformed document must NOT be softened into 'the GPU was busy'."""
    assert ing._is_resource_failure(RuntimeError(msg)) is False


def test_oom_inside_predict_becomes_advisory(monkeypatch):
    """The regression: a CUDA OOM surfaced as PADDLE_PARSE_FAILED with no
    advisory flag, so the UI painted a red GATED row on a 228-page document
    whose pypdf text layer parsed fine. It must be a neutral FALLBACK."""
    monkeypatch.setattr(ing, "_PADDLE_V3_PIPELINE", object())
    monkeypatch.setattr(ing, "_ensure_paddlex_kmeans_guard", lambda: None)

    def _boom(*a, **k):
        raise _FakeOOM("CUDA out of memory. Tried to allocate 2038431744 bytes")

    monkeypatch.setattr(ing, "_paddle_v3_predict", _boom)

    res = ing.parse_pdf_paddle_structure(b"%PDF-1.4 fake")
    assert res["ok"] is False
    assert res["advisory"] is True
    assert res["code"] == "PADDLE_RESOURCE_EXHAUSTED"
    assert "text-layer parser is used instead" in res["reason"]


def test_malformed_predict_failure_is_still_hard(monkeypatch):
    """A genuine parse error keeps the hard code and stays non-advisory —
    the fallback softening must not swallow real document problems."""
    monkeypatch.setattr(ing, "_PADDLE_V3_PIPELINE", object())
    monkeypatch.setattr(ing, "_ensure_paddlex_kmeans_guard", lambda: None)

    def _boom(*a, **k):
        raise ValueError("EOF marker not found")

    monkeypatch.setattr(ing, "_paddle_v3_predict", _boom)

    res = ing.parse_pdf_paddle_structure(b"%PDF-1.4 fake")
    assert res["ok"] is False
    assert res["code"] == "PADDLE_PARSE_FAILED"
    assert res.get("advisory") is not True


def test_release_gpu_cache_never_raises():
    """Cleanup must never turn a successful parse into a failure."""
    ing._release_gpu_cache()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))