"""Shared benchmark harness (§4): manifest → isolated run → compare → artifacts.

Usage from a benchmark test::

    from app.benchmark_harness import BenchmarkCase
    case = BenchmarkCase(suite_id="EU-CBAM-GOLDEN", case_id="steel_bf_001",
                         evidence_class="NORMATIVE", as_of="2026-08-28")
    ... run production ingestion/compile paths to get `actual` ...
    result = case.assert_and_emit(actual, expected, tolerances={...})

Artifacts: benchmark_artifacts/<suite>/<run_id>/{benchmark-result.json,report.md,metrics.json,decisions/}
DB: benchmark_runs row. CI fails on correctness regressions (result != PASS).
"""
from __future__ import annotations
import hashlib, json, os, time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .canonical_models import SCHEMA_VERSION

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "benchmark_artifacts"
CODE_COMMIT = os.getenv("EUROSETU_CODE_COMMIT") or os.getenv("GITHUB_SHA") or "local"


def sha256_bytes(b: bytes) -> str:
    import hashlib as _h
    return _h.sha256(b).hexdigest()


def fixture_manifest(suite_id: str, case_id: str, evidence_class: str,
                     fixture_files: list[dict], expected: dict,
                     scenario: dict, notes: dict | None = None,
                     source: dict | None = None) -> dict:
    return {"suite_id": suite_id, "case_id": case_id, "evidence_class": evidence_class,
            "source": source or {}, "fixture_files": fixture_files,
            "expected": expected, "scenario": scenario,
            "notes": notes or {}, "schema_version": SCHEMA_VERSION}


def _tolerance_ok(expected, actual, tolerance) -> tuple[bool, str]:
    if tolerance is None:
        return (expected == actual, "" if expected == actual else f"expected {expected!r} got {actual!r}")
    try:
        tol = float(tolerance)
        diff = abs(float(actual) - float(expected))
        return (diff <= tol, "" if diff <= tol else f"|{actual}-{expected}|={diff} > {tol}")
    except (TypeError, ValueError):
        return (expected == actual, "" if expected == actual else f"expected {expected!r} got {actual!r}")


def _getpath(obj: dict, dotted: str):
    cur = obj
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None, False
    return cur, True


class BenchmarkCase:
    def __init__(self, suite_id: str, case_id: str, evidence_class: str,
                 as_of: str | None = None, manifest: dict | None = None):
        self.suite_id = suite_id
        self.case_id = case_id
        self.evidence_class = evidence_class
        self.as_of = as_of or "2026-08-28"
        self.manifest = manifest or {}
        self.run_id = str(uuid4())
        self._t0 = time.perf_counter()

    def compare(self, actual: dict, expected: dict,
                tolerances: dict | None = None) -> list[dict]:
        tolerances = tolerances or {}
        out = []
        for field, exp in expected.items():
            act, found = _getpath(actual, field)
            if not found:
                out.append({"name": field, "expected": exp, "actual": None,
                            "tolerance": tolerances.get(field), "pass": False,
                            "detail": "field missing from actual output"})
                continue
            ok, detail = _tolerance_ok(exp, act, tolerances.get(field))
            out.append({"name": field, "expected": exp, "actual": act,
                        "tolerance": tolerances.get(field), "pass": ok, "detail": detail})
        return out

    def emit(self, assertions: list[dict], *, decision_id: str | None = None,
             source_snapshots: list[dict] | None = None,
             extra: dict | None = None) -> dict:
        duration_ms = int((time.perf_counter() - self._t0) * 1000)
        passed = all(a["pass"] for a in assertions)
        result = {"suite_id": self.suite_id, "case_id": self.case_id,
                  "run_id": self.run_id, "code_commit": CODE_COMMIT,
                  "schema_version": SCHEMA_VERSION,
                  "evidence_class": self.evidence_class,
                  "as_of": self.as_of,
                  "source_snapshots": source_snapshots or [],
                  "result": "PASS" if passed else "FAIL",
                  "assertions": assertions, "decision_id": decision_id,
                  "duration_ms": duration_ms,
                  "generated_at": datetime.now(timezone.utc).isoformat(),
                  **(extra or {})}
        dest = ARTIFACTS / self.suite_id.lower().replace("-", "_") / self.run_id
        (dest / "decisions").mkdir(parents=True, exist_ok=True)
        (dest / "benchmark-result.json").write_text(json.dumps(result, indent=2, sort_keys=True))
        (dest / "metrics.json").write_text(json.dumps(
            {"duration_ms": duration_ms, "assertion_count": len(assertions),
             "pass_count": sum(1 for a in assertions if a["pass"]),
             "code_commit": CODE_COMMIT, "schema_version": SCHEMA_VERSION}, indent=2))
        lines = [f"# {self.suite_id} / {self.case_id} - {result['result']}",
                 f"run {self.run_id} · {result['generated_at']} · commit {CODE_COMMIT}", ""]
        for a in assertions:
            mark = "✓" if a["pass"] else "✕"
            lines.append(f"- {mark} `{a['name']}` expected={a['expected']!r} actual={a['actual']!r}"
                         + (f" tol={a['tolerance']}" if a.get("tolerance") else "")
                         + (f" - {a['detail']}" if not a["pass"] and a.get("detail") else ""))
        (dest / "report.md").write_text("\n".join(lines) + "\n")
        try:
            from .db import connect
            with connect() as conn:
                conn.execute("INSERT OR IGNORE INTO benchmark_runs(run_id,suite_id,case_id,result,"
                             "code_commit,schema_version,source_snapshots_json,assertions_json,"
                             "decision_id,duration_ms,generated_at,artifact_path)"
                             " VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                             (self.run_id, self.suite_id, self.case_id, result["result"],
                              CODE_COMMIT, SCHEMA_VERSION,
                              json.dumps(result["source_snapshots"]),
                              json.dumps(assertions), decision_id, duration_ms,
                              result["generated_at"], str(dest.relative_to(ROOT))))
        except Exception:
            pass
        return result

    def assert_and_emit(self, actual: dict, expected: dict,
                        tolerances: dict | None = None, **emit_kw) -> dict:
        assertions = self.compare(actual, expected, tolerances)
        result = self.emit(assertions, **emit_kw)
        failures = [a for a in assertions if not a["pass"]]
        assert result["result"] == "PASS", (
            f"{self.suite_id}/{self.case_id} FAILED: " +
            "; ".join(f"{a['name']}: {a.get('detail') or ('expected=%r actual=%r' % (a['expected'], a['actual']))}" for a in failures))
        return result
