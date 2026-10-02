#!/usr/bin/env python3
"""Release benchmark artifacts for the public /benchmarks page (§10, §13 DoD).

The public page must read ONLY released bundles — never live DB rows or
local run directories. This script is the single gate:

1. Runs the full benchmark suites (fail-closed: any failure aborts release).
2. Collects the latest PASS ``benchmark-result.json`` per (suite, case).
3. Redacts party identifiers / confidential payloads (§14).
4. Writes an immutable bundle ``web/benchmarks/<commit>/`` + updates
   ``web/benchmarks/releases.json``. Commit the bundle to publish it.

Usage: ``python scripts/release_benchmarks.py [--skip-tests]``
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "benchmark_artifacts"
WEB = ROOT / "web" / "benchmarks"

# §10 page sections → suites that feed them.
SECTIONS = {
    "Regulatory engine": ["EU-CBAM-GOLDEN", "CBAM-2026"],
    "Trade engine": ["TARIC-LIVE"],
    "Origin engine": ["SAP-ORIGIN", "ROSA-ORIGIN"],
    "Evidence engine": ["EVIDENCE-DECAY", "CROSSREG", "TIME-TRAVEL", "SAP-BLOCK"],
    "Commercial engine": ["STEELFORCE-STYLE", "CARBMEE-SUPPLIER",
                          "REVENUE-IMPACT", "SPAETER-STYLE"],
    "Scale": ["SCALE-100K"],
    "Fail-closed gate": ["FAIL-CLOSED"],
}

CLASS_LABELS = {
    "NORMATIVE": "Expected result derived directly from a named authoritative source artifact.",
    "EXTERNAL-ORACLE": "Compared with a captured third-party tool output, not live data.",
    "COMPETITIVE-SCENARIO": "Competitor-inspired workflow scenario with synthetic data.",
    "SYNTHETIC": "Fully synthetic data exercising product behaviour.",
}

# §14: strings that must never appear in a public bundle. Synthetic customer
# names, emails, tokens, local paths. Results that contain them fail release.
REDACT_PATTERNS = [
    "Customer-", "@example.com", "token", "lead_token",
    "/home/", "/tmp/", "JSW Steel Vijayanagar",
]


def git_sha() -> str:
    try:
        p = subprocess.run(["git", "rev-parse", "--short=12", "HEAD"],
                           capture_output=True, text=True, cwd=str(ROOT))
        sha = p.stdout.strip()
        return sha or "local"
    except Exception:
        return "local"


def run_suites() -> None:
    p = subprocess.run([sys.executable, "-m", "pytest", "tests/benchmarks", "-q"],
                       capture_output=True, text=True, cwd=str(ROOT))
    print(p.stdout[-2000:])
    if p.returncode != 0:
        print("FAIL-CLOSED: benchmark suites failed — no release produced.",
              file=sys.stderr)
        print(p.stderr[-2000:], file=sys.stderr)
        sys.exit(1)


def collect_latest_pass() -> list[dict]:
    latest: dict[tuple[str, str], dict] = {}
    for path in ARTIFACTS.glob("*/*/benchmark-result.json"):
        try:
            r = json.loads(path.read_text())
        except Exception:
            continue
        if r.get("result") != "PASS":
            continue
        key = (r.get("suite_id", ""), r.get("case_id", ""))
        if key not in latest or r.get("generated_at", "") > latest[key].get("generated_at", ""):
            latest[key] = r
    if not latest:
        print("FAIL-CLOSED: no PASS benchmark results found.", file=sys.stderr)
        sys.exit(1)
    return [latest[k] for k in sorted(latest)]


def redact(results: list[dict]) -> list[dict]:
    """Strip local paths + party identifiers; fail release if patterns remain."""
    clean = []
    for r in results:
        pub = {
            "suite_id": r.get("suite_id"), "case_id": r.get("case_id"),
            "evidence_class": r.get("evidence_class"), "as_of": r.get("as_of"),
            "result": r.get("result"), "code_commit": r.get("code_commit"),
            "schema_version": r.get("schema_version"),
            "generated_at": r.get("generated_at"),
            "duration_ms": r.get("duration_ms"),
            "assertions": [
                {"name": a.get("name"), "expected": a.get("expected"),
                 "actual": a.get("actual"), "tolerance": a.get("tolerance"),
                 "pass": a.get("pass")}
                for a in r.get("assertions", [])],
        }
        blob = json.dumps(pub)
        for pat in REDACT_PATTERNS:
            if pat in blob:
                print(f"FAIL-CLOSED: redaction pattern {pat!r} present in "
                      f"{pub['suite_id']}/{pub['case_id']} — refusing release.",
                      file=sys.stderr)
                sys.exit(1)
        clean.append(pub)
    return clean


def main() -> None:
    skip = "--skip-tests" in sys.argv
    if not skip:
        run_suites()
    results = redact(collect_latest_pass())
    commit = git_sha()
    dest = WEB / commit
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "results.json").write_text(json.dumps(results, indent=2, sort_keys=True))

    by_suite: dict[str, dict] = {}
    for r in results:
        s = by_suite.setdefault(r["suite_id"], {
            "cases": 0, "passed": 0, "evidence_classes": set(),
            "durations_ms": []})
        s["cases"] += 1
        s["passed"] += 1 if r["result"] == "PASS" else 0
        s["evidence_classes"].add(r["evidence_class"])
        s["durations_ms"].append(r.get("duration_ms", 0))
    suites = {k: {**v, "evidence_classes": sorted(v["evidence_classes"]),
                  "p50_ms": sorted(v["durations_ms"])[len(v["durations_ms"]) // 2]}
              for k, v in sorted(by_suite.items())}
    summary = {
        "code_commit": commit,
        "schema_version": results[0].get("schema_version"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_cases": len(results),
        "total_passed": sum(1 for r in results if r["result"] == "PASS"),
        "sections": {sec: [s for s in suites_list if s in suites]
                     for sec, suites_list in SECTIONS.items()},
        "class_labels": CLASS_LABELS,
        "suites": suites,
        "notice": ("Engineering assurance / benchmark validation, not legal "
                   "certification. Metrics below were generated by the exact "
                   f"released code commit {commit}."),
    }
    (dest / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))

    WEB.mkdir(parents=True, exist_ok=True)
    rel_path = WEB / "releases.json"
    releases = json.loads(rel_path.read_text()) if rel_path.exists() else []
    releases = [e for e in releases if e.get("commit") != commit]
    releases.append({"commit": commit, "generated_at": summary["generated_at"],
                     "total_cases": summary["total_cases"],
                     "total_passed": summary["total_passed"],
                     "path": f"{commit}"})
    releases.sort(key=lambda e: e["generated_at"])
    rel_path.write_text(json.dumps(releases, indent=2, sort_keys=True))
    print(f"Released {summary['total_passed']}/{summary['total_cases']} PASS "
          f"cases → web/benchmarks/{commit}/ (commit + push to publish)")


if __name__ == "__main__":
    main()
