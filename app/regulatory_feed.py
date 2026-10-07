"""Tenant-scoped, source-linked regulatory watchlist events.

Only TARIC measure rows with a usable CN code are classified as product
impacts. Other source changes are not silently represented as tariff changes.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from datetime import date, datetime, timezone

from .db import connect


def ensure_tables(conn):
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS regulatory_watchlists(
      id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, cn_code TEXT NOT NULL,
      origin_country TEXT NOT NULL, label TEXT NOT NULL, created_at TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1,
      UNIQUE(tenant_id,cn_code,origin_country));
    CREATE INDEX IF NOT EXISTS idx_reg_watch_tenant ON regulatory_watchlists(tenant_id);
    CREATE TABLE IF NOT EXISTS regulatory_feed_events(
      id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, watchlist_id TEXT NOT NULL,
      dataset TEXT NOT NULL, change_type TEXT NOT NULL, cn_code TEXT NOT NULL,
      origin_country TEXT NOT NULL, effective_from TEXT, old_sha TEXT,
      new_sha TEXT NOT NULL, source_url TEXT NOT NULL, old_record_json TEXT,
      new_record_json TEXT, created_at TEXT NOT NULL,
      FOREIGN KEY(watchlist_id) REFERENCES regulatory_watchlists(id));
    CREATE INDEX IF NOT EXISTS idx_reg_feed_tenant ON regulatory_feed_events(tenant_id,created_at);
    CREATE TABLE IF NOT EXISTS regulatory_feed_reviews(
      id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, event_id TEXT NOT NULL,
      actor TEXT NOT NULL, disposition TEXT NOT NULL, reason TEXT NOT NULL,
      created_at TEXT NOT NULL,
      FOREIGN KEY(event_id) REFERENCES regulatory_feed_events(id));
    CREATE INDEX IF NOT EXISTS idx_reg_feed_reviews ON regulatory_feed_reviews(tenant_id,event_id,created_at);
    """)


def _cn(value):
    return re.sub(r"\D", "", str(value or ""))


def add_watch(tenant_id: str, cn_code: str, origin_country: str, label: str = "") -> dict:
    cn, origin = _cn(cn_code), origin_country.strip().upper()
    if len(cn) != 8 or not re.fullmatch(r"[A-Z]{2}", origin):
        raise ValueError("An eight-digit CN code and two-letter origin country are required")
    if len(label) > 160:
        raise ValueError("Label exceeds 160 characters")
    key = hashlib.sha256(f"{tenant_id}|{cn}|{origin}".encode()).hexdigest()
    with connect() as conn:
        ensure_tables(conn)
        conn.execute("""INSERT INTO regulatory_watchlists(id,tenant_id,cn_code,origin_country,label,created_at,active)
                     VALUES(?,?,?,?,?,?,1) ON CONFLICT(tenant_id,cn_code,origin_country)
                     DO UPDATE SET active=1,label=excluded.label""",
                     (key, tenant_id, cn, origin, label.strip(), datetime.now(timezone.utc).isoformat()))
        return dict(conn.execute("SELECT * FROM regulatory_watchlists WHERE id=?", (key,)).fetchone())


def watches(tenant_id: str) -> list[dict]:
    with connect() as conn:
        ensure_tables(conn)
        return [dict(r) for r in conn.execute(
            "SELECT * FROM regulatory_watchlists WHERE tenant_id=? AND active=1 ORDER BY cn_code,origin_country", (tenant_id,))]


def remove_watch(tenant_id: str, watch_id: str) -> bool:
    with connect() as conn:
        ensure_tables(conn)
        return bool(conn.execute("UPDATE regulatory_watchlists SET active=0 WHERE tenant_id=? AND id=? AND active=1",
                                 (tenant_id, watch_id)).rowcount)


def _rows(records):
    if isinstance(records, dict):
        records = records.get("records") or records.get("measures") or []
    if not isinstance(records, list):
        return None
    out = {}
    for row in records:
        if not isinstance(row, dict):
            return None
        cn = _cn(row.get("cn_code") or row.get("goods_code"))
        if len(cn) < 8:
            continue
        clean = {k: v for k, v in row.items() if k != "source_file"}
        encoded = json.dumps(clean, sort_keys=True, default=str, separators=(",", ":"))
        # Identical duplicate rows represent one measure; a changed value is
        # represented by a removed/added pair unless its stable identity matches.
        identity = (cn, str(row.get("origin_country") or "").upper(),
                    str(row.get("measure_type") or ""), str(row.get("quota_order_number") or ""),
                    str(row.get("additional_code") or ""), str(row.get("valid_from") or ""))
        out.setdefault(identity, {})[hashlib.sha256(encoded.encode()).hexdigest()] = clean
    return out


def _origin_matches(watch: str, measure: str) -> bool:
    return not measure or measure in {watch, "ERGA OMNES", "ALL"}


def _date_matches(as_of: str, old: dict | None, new: dict | None) -> bool:
    row = new or old or {}
    start = str(row.get("valid_from") or "")[:10]
    end = str(row.get("valid_to") or "")[:10]
    return (not start or start <= as_of) and (not end or as_of <= end)


def publish_change(dataset: str, old_sha: str | None, new_sha: str,
                   old_records, new_records, source_url: str, as_of: str,
                   *, delta: bool = False) -> dict:
    """Compare supported normalized rows and persist idempotent matches.

    A first full snapshot establishes a baseline. Delta ZIPs contain only
    changed rows, so their removals cannot be inferred by comparing two ZIPs.
    """
    date.fromisoformat(as_of)
    if not new_sha or old_sha == new_sha:
        return {"status": "UNCHANGED", "events": 0}
    if dataset != "taric_measures":
        return {"status": "UNSUPPORTED_DATASET", "events": 0}
    current = _rows(new_records)
    previous = _rows(old_records)
    if current is None or (old_sha and not delta and previous is None):
        return {"status": "UNCOMPARABLE", "events": 0}
    if not old_sha and not delta:
        return {"status": "BASELINE_CREATED", "events": 0}
    changes = []
    for identity in sorted(set(current) | (set(previous or {}) if not delta else set())):
        before = (previous or {}).get(identity, {}) if not delta else {}
        after = current.get(identity, {})
        if before == after:
            continue
        removed = [before[k] for k in sorted(before.keys() - after.keys())]
        added = [after[k] for k in sorted(after.keys() - before.keys())]
        if len(removed) == len(added) == 1:
            changes.append(("UPDATED", removed[0], added[0]))
        else:
            changes.extend(("REMOVED", row, None) for row in removed)
            changes.extend(("ADDED", None, row) for row in added)
    now = datetime.now(timezone.utc).isoformat()
    count = 0
    with connect() as conn:
        ensure_tables(conn)
        watched = {}
        for item in conn.execute("SELECT * FROM regulatory_watchlists WHERE active=1"):
            watch = dict(item)
            watched.setdefault(watch["cn_code"], []).append(watch)
        for kind, old, new in changes:
            row = new or old
            cn = _cn(row.get("cn_code"))
            origin = str(row.get("origin_country") or "").upper()
            for watch in watched.get(cn[:8], []):
                if not _origin_matches(watch["origin_country"], origin):
                    continue
                old_json = json.dumps(old, sort_keys=True, default=str) if old else None
                new_json = json.dumps(new, sort_keys=True, default=str) if new else None
                event_id = hashlib.sha256(json.dumps([watch["id"],dataset,old_sha,new_sha,kind,old_json,new_json],
                                                    separators=(",", ":")).encode()).hexdigest()
                count += conn.execute("""INSERT OR IGNORE INTO regulatory_feed_events
                  VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                    event_id, watch["tenant_id"], watch["id"], dataset, kind, cn,
                    origin, row.get("valid_from"), old_sha, new_sha, source_url,
                    old_json, new_json, now)).rowcount
    return {"status": "MATCHED", "events": count, "changed_rows": len(changes),
            "comparison": "DELTA_ADDITIONS_ONLY" if delta else "FULL_SNAPSHOT_DIFF"}


def review_event(tenant_id: str, event_id: str, actor: str,
                 disposition: str, reason: str) -> dict:
    if disposition not in {"ACKNOWLEDGED", "ESCALATED", "DISMISSED"}:
        raise ValueError("Invalid disposition")
    reason = reason.strip()
    if len(reason) < 10 or len(reason) > 2000:
        raise ValueError("Review reason must be 10 to 2,000 characters")
    now = datetime.now(timezone.utc).isoformat()
    review_id = hashlib.sha256(f"{event_id}|{actor}|{now}".encode()).hexdigest()
    with connect() as conn:
        ensure_tables(conn)
        if not conn.execute("SELECT 1 FROM regulatory_feed_events WHERE id=? AND tenant_id=?",
                            (event_id, tenant_id)).fetchone():
            raise KeyError(event_id)
        conn.execute("INSERT INTO regulatory_feed_reviews VALUES(?,?,?,?,?,?,?)",
                     (review_id, tenant_id, event_id, actor, disposition, reason, now))
    return {"id": review_id, "event_id": event_id, "actor": actor,
            "disposition": disposition, "reason": reason, "created_at": now}


def events(tenant_id: str, *, as_of: str | None = None, since: str | None = None, limit: int = 100) -> list[dict]:
    if as_of:
        date.fromisoformat(as_of)
    if since:
        date.fromisoformat(since)
    limit = max(1, min(limit, 1000))
    with connect() as conn:
        ensure_tables(conn)
        query = "SELECT * FROM regulatory_feed_events WHERE tenant_id=?"
        args = [tenant_id]
        if as_of:
            query += " AND (effective_from IS NULL OR effective_from<=?)"
            args.append(as_of)
        if since:
            query += " AND created_at>=?"
            args.append(since + "T00:00:00")
        query += " ORDER BY created_at DESC,id DESC LIMIT ?"
        args.append(limit)
        result = [dict(r) for r in conn.execute(query, args)]
    if result:
        latest_reviews = {}
        with connect() as conn:
            for start in range(0, len(result), 500):
                ids = [item["id"] for item in result[start:start + 500]]
                placeholders = ",".join("?" for _ in ids)
                query = f"""SELECT event_id,actor,disposition,reason,created_at FROM
                  regulatory_feed_reviews WHERE tenant_id=? AND event_id IN ({placeholders})
                  ORDER BY created_at DESC,id DESC"""
                for review in conn.execute(query, (tenant_id, *ids)):
                    latest_reviews.setdefault(review["event_id"], dict(review))
        for item in result:
            item["review"] = latest_reviews.get(item["id"])
    for item in result:
        item["old_record"] = json.loads(item.pop("old_record_json")) if item["old_record_json"] else None
        item["new_record"] = json.loads(item.pop("new_record_json")) if item["new_record_json"] else None
    return result


def csv_export(tenant_id: str, as_of: str | None = None, since: str | None = None) -> str:
    fields = ("id", "dataset", "change_type", "cn_code", "origin_country", "effective_from",
              "old_sha", "new_sha", "source_url", "created_at")
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fields)
    writer.writeheader()
    batch = events(tenant_id, as_of=as_of, since=since, limit=1000)
    with connect() as conn:
        ensure_tables(conn)
        count = conn.execute("SELECT COUNT(*) FROM regulatory_feed_events WHERE tenant_id=?" +
                             (" AND created_at>=?" if since else ""),
                             (tenant_id, since + "T00:00:00") if since else (tenant_id,)).fetchone()[0]
    if count > 1000:
        raise ValueError("CSV export exceeds 1,000 events; narrow the since date")
    for event in batch:
        writer.writerow({k: event.get(k) for k in fields})
    return buf.getvalue()


def refresh_status() -> dict:
    """Observed TARIC refresh freshness; no contractual SLA is inferred."""
    from .source_resolvers import latest_manifest
    from .source_sync import NORMALIZED
    manifest = latest_manifest("taric_measures")
    auto = NORMALIZED / "taric_measures" / "latest.json"
    if auto.exists():
        candidate = json.loads(auto.read_text())
        if not manifest or candidate.get("retrieved_at", "") > manifest.get("retrieved_at", ""):
            manifest = candidate
    if not manifest:
        return {"dataset": "taric_measures", "status": "NO_SNAPSHOT"}
    stamp = manifest.get("retrieved_at")
    if not stamp:
        return {"dataset": "taric_measures", "status": "UNKNOWN_AGE", "snapshot": manifest.get("sha256")}
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(stamp.replace("Z", "+00:00"))).total_seconds() / 3600
    return {"dataset": "taric_measures", "status": "FRESH" if 0 <= age <= 48 else "STALE",
            "age_hours": round(age, 1), "refresh_target_hours": 48,
            "retrieved_at": stamp, "snapshot": manifest.get("sha256"),
            "source_url": manifest.get("source_url") or manifest.get("source"),
            "authority": manifest.get("authority"),
            "legal_authority": manifest.get("legal_authority")}
