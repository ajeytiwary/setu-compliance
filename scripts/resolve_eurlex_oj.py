#!/usr/bin/env python3
"""Resolve a CELEX number to its OJ HTML URL on EUR-Lex, programmatically.

EUR-Lex itself blocks urllib (AWS WAF returns an empty 202), but the
Publications Office Cellar semantic API does not. The Cellar RDF for a CELEX
number contains owl:sameAs links to the OJ resource IDs (e.g. L_202601457),
which map 1:1 to the OJ HTML URL used by the browser.

Usage:
    python scripts/resolve_eurlex_oj.py 32026R1457
    python scripts/resolve_eurlex_oj.py 32026R1457 --json

Output: the OJ HTML URL (or JSON with all OJ IDs found).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36 SetuCompliance/0.8"}
CELLAR_CELEX = "https://publications.europa.eu/resource/celex/{celex}"


def resolve_celex(celex: str, timeout: int = 30) -> list[str]:
    """Return the OJ resource IDs (e.g. L_202601457) for a CELEX number.

    The Cellar RDF lists many related works (amending regulations, base
    regulations, treaties). The work's *own* OJ is the rdf:Description whose
    `about` IS an OJ resource with cdm#work type and a self-referential oj link.
    """
    celex = celex.strip().upper()
    req = urllib.request.Request(CELLAR_CELEX.format(celex=celex), headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read().decode("utf-8", "replace")

    own = []
    for m in re.finditer(r'<rdf:Description rdf:about="([^"]+)">(.*?)</rdf:Description>', body, re.S):
        about, inner = m.group(1), m.group(2)
        oj = re.search(r"resource/oj/([A-Z]_[0-9]{8,9})", about)
        if oj and "cdm#work" in inner and f"resource/oj/{oj.group(1)}" in inner:
            own.append(oj.group(1))
    if own:
        return sorted(set(own))

    # Fallback: any OJ resource mentioned (may include amending regs)
    return sorted(set(re.findall(r"resource/oj/([A-Z]_[0-9]{8,9})", body)))


def oj_to_url(oj_id: str) -> str:
    """Map an OJ resource ID to the EUR-Lex OJ HTML URL."""
    return f"https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=OJ:{oj_id}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("celex", help="CELEX number, e.g. 32026R1457")
    ap.add_argument("--json", action="store_true", help="emit JSON")
    args = ap.parse_args()

    ojs = resolve_celex(args.celex)
    if not ojs:
        print(f"no OJ resource found for CELEX {args.celex}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps({"celex": args.celex.upper(), "oj_ids": ojs, "urls": [oj_to_url(o) for o in ojs]}, indent=2))
    else:
        print(oj_to_url(ojs[0]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())