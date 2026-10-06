import io
import sqlite3

import pytest

from app import db
from app.real_evidence import create
from app.recovery import backup_and_drill


class MemoryObjectStore:
    def __init__(self):
        self.objects = {}

    def put_object(self, **request):
        self.objects[(request['Bucket'], request['Key'])] = bytes(request['Body'])
        assert request['ServerSideEncryption'] == 'AES256'

    def get_object(self, **request):
        return {'Body': io.BytesIO(self.objects[(request['Bucket'], request['Key'])])}


def test_offhost_readback_restore_drill_records_verified_recovery(monkeypatch, tmp_path):
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'operational.db')
    db.init_db()
    dossier = create('tenant-a', 'author', 'Recovery test')
    store = MemoryObjectStore()
    result = backup_and_drill('tenant-a', 'test-bucket', 'customer-backups', store)
    assert result['backup_sha256'] == result['restored_sha256']
    assert result['event_count'] >= 1
    assert result['object_uri'].startswith('s3://test-bucket/customer-backups/tenant-a/')
    with db.connect() as conn:
        row = conn.execute('SELECT * FROM recovery_drills WHERE id=?', (result['id'],)).fetchone()
        assert row['tenant_id'] == 'tenant-a'
        assert row['restored_sha256'] == result['restored_sha256']
    assert len(store.objects) == 2


def test_readback_corruption_cannot_record_success(monkeypatch, tmp_path):
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'operational.db')
    db.init_db()
    create('tenant-a', 'author', 'Recovery test')

    class CorruptStore(MemoryObjectStore):
        def get_object(self, **request):
            result = super().get_object(**request)
            if request['Key'].endswith('.db'):
                result['Body'] = io.BytesIO(b'corrupt')
            return result

    with pytest.raises((ValueError, sqlite3.DatabaseError)):
        backup_and_drill('tenant-a', 'test-bucket', 'customer-backups', CorruptStore())
    with db.connect() as conn:
        assert conn.execute("SELECT name FROM sqlite_master WHERE name='recovery_drills'").fetchone() is None
