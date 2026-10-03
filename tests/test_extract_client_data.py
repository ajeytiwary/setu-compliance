"""Tests for scripts/extract_client_data.py — batch orchestration only.

The parser itself is covered by tests/test_document_ingest*.py; what matters
here is that a re-extraction can never make the batch worse than it was.
"""

import importlib.util
from pathlib import Path

import pytest

SCRIPT = (Path(__file__).resolve().parent.parent
          / "scripts" / "extract_client_data.py")


def _load():
    spec = importlib.util.spec_from_file_location("extract_client_data", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


pick_best = _load().pick_best


def _r(parser, chars=100, cns=None, ok=True):
    return {"parser": parser, "ok": ok, "chars": chars, "cns_found": cns or []}


def test_empty_parse_never_wins():
    """A parser can report ok=True and still return nothing. That must not be
    selected — otherwise `--force` without --with-paddle silently replaces a
    good paddle extraction with an empty pypdf one."""
    assert pick_best([_r("pypdf", chars=0)]) is None


def test_empty_parse_does_not_beat_real_text():
    comp = [_r("paddle-structure-v3", chars=2176, cns=["02611858"]),
            _r("pypdf", chars=0)]
    best = pick_best(comp)
    assert best["parser"] == "paddle-structure-v3"
    assert best["chars"] == 2176


def test_cn_count_outranks_parser_priority():
    """Content beats parser rank: pypdf finding a CN is more useful than a
    clean parse that found nothing."""
    best = pick_best([_r("paddle-structure-v3", chars=50),
                      _r("pypdf", chars=40, cns=["1234"])])
    assert best["parser"] == "pypdf"


def test_all_failed_returns_none():
    assert pick_best([_r("pypdf", ok=False),
                      _r("paddle-structure-v3", ok=False)]) is None


def test_empty_input_returns_none():
    assert pick_best([]) is None


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))