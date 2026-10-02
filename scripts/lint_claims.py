#!/usr/bin/env python3
"""Legal/claim lint for benchmark + public copy (§9 CI gate, §15 claims discipline).

Fails if any forbidden positive claim appears in benchmark-adjacent copy or
public pages. Negated guardrails ("not legal certification") are required
elsewhere and are NOT matched — patterns below only match positive claims.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Positive claims that require evidence we do not hold. Each is a regex
# matched case-insensitively. Keep narrow: negated forms must keep passing.
FORBIDDEN = [
    r"EU[\s-]?certified",
    r"legally certified",
    r"certified by (the )?(European|EU)",
    r"replaces (SAP )?GTS",
    r"parity with (SAP|Steelforce|CarbonChain|Carbmee|Spaeter|Osapiens)",
    r"production[\s-]?proven at enterprise scale",
    r"end-to-end guarantee of (customs|CBAM|quota)",
    r"guaranteed (customs clearance|CBAM acceptance|quota allocation)",
]

SCAN_GLOBS = [
    "app/static/benchmarks.html",
    "app/static/case-study.html",
    "app/static/benchmarks.js",
    "app/static/case-study.js",
    "web/benchmarks/**/*.json",
    "specs/benchmark-suite.md",
]


def main() -> int:
    failures = []
    files = []
    for g in SCAN_GLOBS:
        files.extend(ROOT.glob(g))
    if not files:
        print("claim-lint: no benchmark copy files found — nothing to check")
        return 0
    for path in sorted(files):
        try:
            text = path.read_text()
        except Exception:
            continue
        for pat in FORBIDDEN:
            for m in re.finditer(pat, text, re.IGNORECASE):
                line = text[:m.start()].count("\n") + 1
                failures.append(f"{path.relative_to(ROOT)}:{line}: {m.group(0)!r}")
    if failures:
        print("CLAIM-LINT FAILED — positive claims without evidence:", file=sys.stderr)
        for f in failures:
            print(f"  {f}", file=sys.stderr)
        return 1
    print(f"claim-lint OK ({len(files)} files, {len(FORBIDDEN)} patterns)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
