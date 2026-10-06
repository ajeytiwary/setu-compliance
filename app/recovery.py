"""Off-host, read-back verified SQLite recovery drills for isolated tenants."""
from __future__ import annotations

import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from . import db
from scripts.sqlite_backup import backup, restore

SCHEMA = '''
CREATE TABLE IF NOT EXISTS recovery_drills (
 id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, object_uri TEXT NOT NULL,
 backup_sha256 TEXT NOT NULL, restored_sha256 TEXT NOT NULL,
 document_count INTEGER NOT NULL, event_count INTEGER NOT NULL,
 completed_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_recovery_drills_tenant ON recovery_drills(tenant_id,completed_at);
'''


def _counts(path: Path) -> tuple[int, int]:
    import sqlite3
    with sqlite3.connect(f'file:{path}?mode=ro', uri=True) as conn:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        return tuple(conn.execute(f'SELECT COUNT(*) FROM {name}').fetchone()[0] if name in tables else 0
                     for name in ('real_documents', 'real_events'))


def backup_and_drill(tenant_id: str, bucket: str, prefix: str, client=None) -> dict:
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{1,79}', tenant_id):
        raise ValueError('INVALID_TENANT_ID')
    if not bucket or not db.DB_PATH.is_file():
        raise ValueError('BACKUP_BUCKET_OR_SOURCE_MISSING')
    if client is None:
        import boto3
        client = boto3.client('s3')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    key = f'{prefix.strip("/") + "/" if prefix.strip("/") else ""}{tenant_id}/{stamp}-{uuid4().hex}.db'
    with tempfile.TemporaryDirectory(prefix='eurosetu-recovery-') as temp:
        root = Path(temp)
        local_backup = root / 'source.db'
        manifest = backup(db.DB_PATH, local_backup, tenant_id)
        manifest_file = local_backup.with_suffix('.db.json')
        client.put_object(Bucket=bucket, Key=key, Body=local_backup.read_bytes(), ServerSideEncryption='AES256',
                          ContentType='application/vnd.sqlite3', Metadata={'tenant-id': tenant_id, 'sha256': manifest['sha256']})
        client.put_object(Bucket=bucket, Key=key + '.json', Body=manifest_file.read_bytes(),
                          ServerSideEncryption='AES256', ContentType='application/json')
        fetched = root / 'fetched.db'
        fetched.write_bytes(client.get_object(Bucket=bucket, Key=key)['Body'].read())
        fetched.with_suffix('.db.json').write_bytes(client.get_object(Bucket=bucket, Key=key + '.json')['Body'].read())
        recovered = root / 'restored.db'
        restore(fetched, recovered, tenant_id)
        source_counts, restored_counts = _counts(local_backup), _counts(recovered)
        if source_counts != restored_counts:
            raise ValueError('RECOVERY_ROW_COUNT_MISMATCH')
        from scripts.sqlite_backup import _sha256
        restored_sha = _sha256(recovered)
        if restored_sha != manifest['sha256']:
            raise ValueError('RECOVERY_HASH_MISMATCH')
        result = {'id': str(uuid4()), 'tenant_id': tenant_id, 'object_uri': f's3://{bucket}/{key}',
                  'backup_sha256': manifest['sha256'], 'restored_sha256': restored_sha,
                  'document_count': source_counts[0], 'event_count': source_counts[1],
                  'completed_at': datetime.now(timezone.utc).isoformat()}
        with db.connect() as conn:
            conn.executescript(SCHEMA)
            conn.execute('INSERT INTO recovery_drills(id,tenant_id,object_uri,backup_sha256,restored_sha256,document_count,event_count,completed_at) VALUES(?,?,?,?,?,?,?,?)',
                         tuple(result[k] for k in ('id','tenant_id','object_uri','backup_sha256','restored_sha256','document_count','event_count','completed_at')))
        return result
