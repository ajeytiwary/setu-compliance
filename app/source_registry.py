"""Source registry (§2.1): immutable versioned regulatory snapshots.

Never overwrites a historical snapshot — new retrieval = new row with new hash.
"""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib, json
from .db import connect, rows, row
from .canonical_models import SCHEMA_VERSION


def register(*, source_id: str, authority: str, title: str, legal_basis: list[str],
             version: str, effective_from: str | None = None,
             effective_to: str | None = None, content: bytes | str = b"",
             parser_version: str = "v1") -> dict:
    raw = content.encode() if isinstance(content, str) else content
    digest = hashlib.sha256(raw).hexdigest()
    now = datetime.now(timezone.utc).isoformat()
    rec = {"source_id": source_id, "schema_version": SCHEMA_VERSION, "authority": authority,
           "title": title, "legal_basis": legal_basis, "version": version,
           "retrieved_at": now, "effective_from": effective_from,
           "effective_to": effective_to, "content_hash": digest,
           "parser_version": parser_version}
    with connect() as conn:
        conn.execute("INSERT OR IGNORE INTO source_snapshots(source_id,version,content_hash,payload_json,created_at)"
                     " VALUES(?,?,?,?,?)",
                     (source_id, version, digest, json.dumps(rec), now))
    return rec


def snapshot_ref(source_id: str, version: str) -> dict | None:
    with connect() as conn:
        r = row(conn, "SELECT payload_json FROM source_snapshots WHERE source_id=? AND version=?",
                (source_id, version))
        return json.loads(r["payload_json"]) if r else None


def effective_at(as_of: str) -> list[dict]:
    """All snapshots effective on a date — for point-in-time compile (§5.12)."""
    with connect() as conn:
        try:
            all_snaps = rows(conn, "SELECT payload_json FROM source_snapshots")
        except Exception:
            return []
    out = []
    for r in all_snaps:
        p = json.loads(r["payload_json"])
        if ((not p.get("effective_from") or as_of >= p["effective_from"])
                and (not p.get("effective_to") or as_of <= p["effective_to"])):
            out.append({"id": p["source_id"], "sha256": p["content_hash"], "version": p["version"]})
    return out
