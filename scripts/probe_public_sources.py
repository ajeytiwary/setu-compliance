#!/usr/bin/env python3
"""Probe live public sources (Layer 1/2/3 registry health) without scraping.

For each entry in config/public_evidence_sources.json, issues a lightweight
HEAD/GET (direct files + landing pages) and records HTTP status, content-type,
bytes, and sha256 of the first 64KB. Never downloads full datasets here;
use build_public_evidence_corpus.py --acquire for direct files only.
Writes data/public_trade_evidence/source_probe.json (gitignored).
"""
from __future__ import annotations
import hashlib, json, urllib.request
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "config/public_evidence_sources.json"
OUT = ROOT / "data/public_trade_evidence/source_probe.json"

def probe(url: str, timeout: int = 20) -> dict:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "EuroSetu-public-evidence-corpus/1"}, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return {"ok": True, "status": r.status, "content_type": r.headers.get("Content-Type", "")}
    except Exception as e1:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "EuroSetu-public-evidence-corpus/1", "Range": "bytes=0-65535"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                head = r.read(65536)
                return {"ok": True, "status": getattr(r, "status", 200),
                        "content_type": r.headers.get("Content-Type", ""),
                        "sample_bytes": len(head),
                        "sample_sha256": hashlib.sha256(head).hexdigest()}
        except Exception as e2:
            return {"ok": False, "error": f"{e1} / {e2}"[:300]}

def main() -> None:
    cfg = json.loads(CFG.read_text())
    results = []
    for s in cfg["sources"]:
        r = probe(s["url"])
        results.append({"id": s["id"], "source_class": s.get("source_class"),
                        "kind": s.get("kind"), "url": s["url"],
                        "license": s.get("license"), **r,
                        "probed_at": datetime.now(timezone.utc).isoformat()})
        print(f"{s['id']}: {'OK '+str(r.get('status')) if r.get('ok') else 'FAIL '+str(r.get('error'))[:100]}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"generated_at": datetime.now(timezone.utc).isoformat(), "sources": results}, indent=2, sort_keys=True) + "\n")
    print(f"wrote {OUT}")

if __name__ == "__main__":
    main()
