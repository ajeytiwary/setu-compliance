from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import db
from app.main import app
from app.pilot_keys import mint_pilot_key
from scripts.sqlite_backup import backup, restore


def test_backup_restore_preserves_real_dossier_and_rejects_wrong_tenant(monkeypatch, tmp_path):
    db_path = tmp_path / 'operational.db'
    monkeypatch.setattr(db, 'DB_PATH', db_path)
    db.init_db()
    from app.real_evidence import create, get
    dossier_id = create('tenant-a', 'author', 'Recovery fixture')
    with db.connect() as conn:
        conn.execute("INSERT INTO real_documents(id,dossier_id,filename,sha256,blob,parsed_json,role,uploaded_by,review_status,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)", ('document-1', dossier_id, 'source.pdf', 'hash', b'%PDF-client-evidence', '{}', 'INVOICE', 'author', 'PENDING', '2026-10-05T00:00:00Z'))
    archived = tmp_path / 'backup.db'
    manifest = backup(db_path, archived, 'tenant-a')
    assert manifest['bytes'] > 0
    with pytest.raises(ValueError, match='TENANT_MISMATCH'):
        restore(archived, tmp_path / 'wrong.db', 'tenant-b')
    recovered = tmp_path / 'recovered.db'
    restore(archived, recovered, 'tenant-a')
    monkeypatch.setattr(db, 'DB_PATH', recovered)
    assert get(dossier_id, 'tenant-a')['dossier']['name'] == 'Recovery fixture'
    with db.connect() as conn:
        assert conn.execute('SELECT blob FROM real_documents WHERE id=?', ('document-1',)).fetchone()[0] == b'%PDF-client-evidence'
    with pytest.raises(KeyError):
        get(dossier_id, 'tenant-b')
    assert not (tmp_path / 'wrong.db').exists()


def test_backup_refuses_wrong_or_mixed_tenant_snapshot(monkeypatch, tmp_path):
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'operational.db')
    db.init_db()
    from app.real_evidence import create
    create('tenant-a', 'author', 'Owned')
    with pytest.raises(RuntimeError, match='another tenant'):
        backup(db.DB_PATH, tmp_path / 'wrong-tenant.db', 'tenant-b')
    assert not (tmp_path / 'wrong-tenant.db').exists()
    create('tenant-b', 'author', 'Other customer')
    with pytest.raises(RuntimeError, match='another tenant'):
        backup(db.DB_PATH, tmp_path / 'mixed-tenant.db', 'tenant-a')
    assert not (tmp_path / 'mixed-tenant.db').exists()


def test_backup_refuses_orphaned_client_document(monkeypatch, tmp_path):
    import sqlite3
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'operational.db')
    db.init_db()
    from app.real_evidence import create
    create('tenant-a', 'author', 'Owned')
    with sqlite3.connect(db.DB_PATH) as conn:
        conn.execute("INSERT INTO real_documents(id,dossier_id,filename,sha256,blob,parsed_json,role,uploaded_by,review_status,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)", ('orphan', 'missing-dossier', 'sensitive.pdf', 'hash', b'client data', '{}', 'INVOICE', 'author', 'PENDING', 'now'))
    with pytest.raises(RuntimeError, match='broken foreign-key'):
        backup(db.DB_PATH, tmp_path / 'orphan.db', 'tenant-a')
    assert not (tmp_path / 'orphan.db').exists()


def test_production_rejects_unhosted_tenant_and_reports_database_readiness(monkeypatch, tmp_path):
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'operational.db')
    monkeypatch.setenv('EUROSETU_ENV', 'production')
    monkeypatch.setenv('EUROSETU_DEPLOYMENT_TENANT', 'tenant-a')
    monkeypatch.setenv('EUROSETU_JWT_SECRET', 'test-secret')
    monkeypatch.delenv('DATABASE_URL', raising=False)
    with TestClient(app) as client:
        assert client.get('/health/ready').json() == {'status': 'ready'}
        assert client.get('/api/shipments/anything').status_code == 404
        assert client.get('/v1/decisions/anything').status_code == 404
        assert client.get('/internal/benchmarks/runs').status_code == 404
        token = mint_pilot_key('test-secret', 'tenant-b', ['pilot_contributor'], 1, 'other@example.test')
        headers = {'Authorization': 'Bearer ' + token, 'x-eurosetu-tenant': 'tenant-b'}
        response = client.post('/api/real-dossiers', json={'name': 'Denied'}, headers=headers)
        assert response.status_code == 403
        assert 'not hosted' in response.json()['detail']


def test_production_rejects_misleading_postgres_url(monkeypatch, tmp_path):
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'operational.db')
    monkeypatch.setenv('EUROSETU_ENV', 'production')
    monkeypatch.setenv('EUROSETU_DEPLOYMENT_TENANT', 'tenant-a')
    monkeypatch.setenv('EUROSETU_JWT_SECRET', 'test-secret')
    monkeypatch.setenv('DATABASE_URL', 'postgresql://example.invalid/eurosetu')
    with pytest.raises(RuntimeError, match='DATABASE_URL is unsupported'):
        with TestClient(app):
            pass


def test_single_tenant_storage_rejects_mixed_and_legacy_data(monkeypatch, tmp_path):
    from app.production_storage import validate_single_tenant_storage
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'operational.db')
    db.init_db()
    validate_single_tenant_storage('tenant-a')
    from app.real_evidence import create
    create('tenant-a', 'author', 'Owned')
    validate_single_tenant_storage('tenant-a')
    create('tenant-b', 'author', 'Wrong deployment')
    with pytest.raises(RuntimeError, match='another tenant'):
        validate_single_tenant_storage('tenant-a')
    with db.connect() as conn:
        conn.execute("DELETE FROM real_events WHERE dossier_id IN (SELECT id FROM real_dossiers WHERE tenant_id=?)", ('tenant-b',))
        conn.execute('DELETE FROM real_dossiers WHERE tenant_id=?', ('tenant-b',))
        conn.execute("INSERT INTO suppliers(id,name,country,created_at,updated_at) VALUES(?,?,?,?,?)", ('supplier-1','Legacy','IN','now','now'))
    with pytest.raises(RuntimeError, match='unscoped operational'):
        validate_single_tenant_storage('tenant-a')


def test_recurring_saas_activation_fails_closed_without_real_release_and_recovery(monkeypatch, tmp_path):
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'operational.db')
    monkeypatch.setenv('EUROSETU_ENV', 'production')
    monkeypatch.setenv('EUROSETU_DEPLOYMENT_TENANT', 'tenant-a')
    monkeypatch.setenv('EUROSETU_JWT_SECRET', 'test-secret')
    monkeypatch.setenv('EUROSETU_BACKUP_BUCKET', 'approved-test-bucket')
    monkeypatch.setenv('EUROSETU_RECURRING_SAAS_ENABLED', '1')
    monkeypatch.delenv('DATABASE_URL', raising=False)
    with pytest.raises(RuntimeError, match='Recurring SaaS release gate closed'):
        with TestClient(app):
            pass
    monkeypatch.setenv('EUROSETU_RECURRING_SAAS_ENABLED', '0')
    with TestClient(app) as client:
        token = mint_pilot_key('test-secret', 'tenant-a', ['admin'], 1, 'admin@example.test')
        response = client.get('/api/commercial/readiness', headers={'Authorization': 'Bearer ' + token, 'x-eurosetu-tenant': 'tenant-a'})
        assert response.status_code == 200
        gate = response.json()
        assert gate['ready_for_recurring_saas'] is False
        assert 'REAL_REVIEWER_APPROVED_READY_DOSSIER_REQUIRED' in gate['blockers']
        assert 'OFF_HOST_RESTORE_DRILL_REQUIRED' in gate['blockers']


def test_production_admin_can_revoke_one_principal_without_affecting_other_users(monkeypatch, tmp_path):
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'operational.db')
    monkeypatch.setenv('EUROSETU_ENV', 'production')
    monkeypatch.setenv('EUROSETU_DEPLOYMENT_TENANT', 'tenant-a')
    monkeypatch.setenv('EUROSETU_JWT_SECRET', 'test-secret')
    monkeypatch.delenv('DATABASE_URL', raising=False)
    def headers(subject, roles):
        token = mint_pilot_key('test-secret', 'tenant-a', roles, 1, subject)
        return {'Authorization': 'Bearer ' + token, 'x-eurosetu-tenant': 'tenant-a'}
    admin = headers('admin@example.test', ['admin'])
    viewer = headers('viewer@example.test', ['pilot_viewer'])
    other = headers('other@example.test', ['pilot_viewer'])
    with TestClient(app) as client:
        created = client.post('/api/real-dossiers', json={'name': 'Revocation fixture'}, headers=admin)
        assert created.status_code == 201
        dossier_id = created.json()['dossier']['id']
        path = f'/api/real-dossiers/{dossier_id}'
        assert client.get(path, headers=viewer).status_code == 200
        denied = client.post('/api/admin/revoke-principal', json={'subject': 'viewer@example.test', 'reason': 'Pilot access withdrawn'}, headers=viewer)
        assert denied.status_code == 403
        revoked = client.post('/api/admin/revoke-principal', json={'subject': 'viewer@example.test', 'reason': 'Pilot access withdrawn'}, headers=admin)
        assert revoked.status_code == 200, revoked.text
        assert client.get(path, headers=viewer).status_code == 401
        assert client.get(path, headers=other).status_code == 200
        with db.connect() as conn:
            record = conn.execute('SELECT actor,reason FROM principal_revocations WHERE tenant_id=? AND subject=?', ('tenant-a', 'viewer@example.test')).fetchone()
        assert tuple(record) == ('admin@example.test', 'Pilot access withdrawn')
