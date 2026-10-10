"""Fail-closed ownership checks for the isolated single-tenant production database."""
from __future__ import annotations

from .db import connect

TENANT_TABLES = ('real_dossiers', 'real_release_packets', 'recovery_drills', 'pilot_dossiers', 'evidence_objects', 'principal_revocations', 'real_source_signoffs', 'regulatory_watchlists', 'regulatory_feed_events', 'regulatory_feed_reviews')
LEGACY_OPERATIONAL_TABLES = (
    'shipments', 'requirements', 'evidence', 'verifications', 'suppliers',
    'integration_runs', 'canonical_records', 'genealogy_edges', 'activity_records',
    'trade_documents', 'supplier_evidence_records', 'cbam_calculations',
    'origin_evaluations', 'canonical_decisions',
)


def validate_single_tenant_connection(conn, tenant_id: str) -> None:
    if not tenant_id or tenant_id == 'default':
        raise RuntimeError('Production requires a non-default tenant ID')
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if conn.execute('PRAGMA foreign_key_check').fetchone():
        raise RuntimeError('Production database contains broken foreign-key references')
    for name in TENANT_TABLES:
        if name in tables:
            count = conn.execute(f'SELECT COUNT(*) FROM {name} WHERE tenant_id IS NULL OR tenant_id<>?', (tenant_id,)).fetchone()[0]
            if count:
                raise RuntimeError(f'Production database contains records owned by another tenant: {name}')
    for name in LEGACY_OPERATIONAL_TABLES:
        if name in tables and conn.execute(f'SELECT 1 FROM {name} LIMIT 1').fetchone():
            raise RuntimeError(f'Production database contains unscoped operational records: {name}')


def validate_single_tenant_storage(tenant_id: str) -> None:
    with connect() as conn:
        validate_single_tenant_connection(conn, tenant_id)
