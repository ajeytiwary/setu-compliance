"""Consistent SQLite backup, verification, and offline restore for a tenant deployment.

Run backup against the mounted database. Restore only into a new, non-existing path;
stop the app and swap that verified file during a documented recovery operation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _check(path: Path, tenant_id: str) -> None:
    with sqlite3.connect(f'file:{path}?mode=ro', uri=True) as conn:
        result = conn.execute('PRAGMA integrity_check').fetchone()[0]
        if result != 'ok':
            raise ValueError(f'SQLITE_INTEGRITY_FAILED: {result}')
        required = {'shipments', 'real_dossiers', 'real_documents', 'real_events'}
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not required.issubset(tables):
            raise ValueError('REQUIRED_TABLES_MISSING')
        from app.production_storage import validate_single_tenant_connection
        validate_single_tenant_connection(conn, tenant_id)


def backup(source: Path, destination: Path, tenant_id: str) -> dict:
    if not tenant_id:
        raise ValueError('TENANT_REQUIRED')
    if not source.is_file() or destination.exists() or destination.with_suffix(destination.suffix + '.json').exists():
        raise ValueError('SOURCE_MISSING_OR_DESTINATION_EXISTS')
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with sqlite3.connect(f'file:{source}?mode=ro', uri=True) as src, sqlite3.connect(destination) as dst:
            src.backup(dst)
        _check(destination, tenant_id)
        manifest = {'tenant_id': tenant_id, 'created_at': datetime.now(timezone.utc).isoformat(),
                    'sha256': _sha256(destination), 'bytes': destination.stat().st_size,
                    'format': 'sqlite3-online-backup-v1'}
        destination.with_suffix(destination.suffix + '.json').write_text(json.dumps(manifest, sort_keys=True) + '\n')
        return manifest
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def restore(backup_path: Path, destination: Path, tenant_id: str) -> dict:
    manifest_path = backup_path.with_suffix(backup_path.suffix + '.json')
    manifest = json.loads(manifest_path.read_text())
    if manifest['tenant_id'] != tenant_id:
        raise ValueError('TENANT_MISMATCH')
    if _sha256(backup_path) != manifest['sha256'] or backup_path.stat().st_size != manifest['bytes']:
        raise ValueError('BACKUP_HASH_MISMATCH')
    _check(backup_path, tenant_id)
    if destination.exists():
        raise ValueError('RESTORE_DESTINATION_EXISTS')
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with sqlite3.connect(f'file:{backup_path}?mode=ro', uri=True) as src, sqlite3.connect(destination) as dst:
            src.backup(dst)
        _check(destination, tenant_id)
        if _sha256(destination) != manifest['sha256']:
            raise ValueError('RESTORE_HASH_MISMATCH')
        return manifest
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['backup', 'restore'])
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--tenant', required=True)
    args = parser.parse_args()
    result = backup(args.source, args.destination, args.tenant) if args.action == 'backup' else restore(args.source, args.destination, args.tenant)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
