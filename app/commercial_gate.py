"""Fail-closed activation gate for recurring operational SaaS."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone

from . import db
from .production_storage import validate_single_tenant_storage


def assess(tenant_id: str, *, quick: bool = False) -> dict:
    blockers = []
    try:
        validate_single_tenant_storage(tenant_id)
    except RuntimeError:
        blockers.append('PRODUCTION_TENANT_STORAGE_INVALID')
    bucket = os.getenv('EUROSETU_BACKUP_BUCKET', '').strip()
    if not bucket:
        blockers.append('OFF_HOST_BACKUP_NOT_CONFIGURED')
    with db.connect() as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if quick:
            dossiers = [row[0] for row in conn.execute("SELECT dossier_id FROM real_source_signoffs WHERE tenant_id=? AND status='APPROVED' GROUP BY dossier_id ORDER BY MAX(rowid) DESC", (tenant_id,))] if 'real_source_signoffs' in tables else []
        else:
            dossiers = [row[0] for row in conn.execute('SELECT id FROM real_dossiers WHERE tenant_id=?', (tenant_id,))] if 'real_dossiers' in tables else []
        drill = conn.execute('SELECT * FROM recovery_drills WHERE tenant_id=? ORDER BY completed_at DESC LIMIT 1', (tenant_id,)).fetchone() if 'recovery_drills' in tables else None
    ready_ids = []
    verified_at = {}
    from .real_evidence import get
    from .customer_source import approved_at_for
    for dossier_id in dossiers:
        try:
            state = get(dossier_id, tenant_id)
            if state['decision'] == 'READY':
                ready_ids.append(dossier_id)
                signed_at = approved_at_for(state)
                if signed_at:
                    verified_at[dossier_id] = signed_at
                    if quick:
                        break
        except (ValueError, KeyError):
            continue
    with db.connect() as conn:
        if 'real_release_packets' not in tables:
            approved = []
        elif quick:
            candidate = next(iter(verified_at), ready_ids[0] if ready_ids else None)
            approved = [dict(row) for row in conn.execute("SELECT * FROM real_release_packets WHERE tenant_id=? AND dossier_id=? AND status='APPROVED'", (tenant_id,candidate))] if candidate else []
        else:
            approved = [dict(row) for row in conn.execute("SELECT * FROM real_release_packets WHERE tenant_id=? AND status='APPROVED'", (tenant_id,))]
    if ready_ids and not verified_at:
        blockers.append('INDEPENDENT_CUSTOMER_SOURCE_SIGNOFF_REQUIRED')
    release_at = None
    if not ready_ids:
        blockers.append('REAL_REVIEWER_APPROVED_READY_DOSSIER_REQUIRED')
    else:
        attested = False
        for row in approved:
            if row['dossier_id'] in ready_ids:
                try:
                    packet = json.loads(row['packet_json'])
                    if packet.get('source_kind') == 'REAL_CLIENT_SHIPMENT' and packet.get('source_attestation'):
                        attested = True
                        if row['dossier_id'] in verified_at:
                            when = max(datetime.fromisoformat(row['reviewed_at']), datetime.fromisoformat(verified_at[row['dossier_id']]))
                            if release_at is None or when > release_at:
                                release_at = when
                except (TypeError, ValueError):
                    pass
        if not attested:
            blockers.append('REAL_SOURCE_ATTESTATION_REQUIRED')
    if drill is None:
        blockers.append('OFF_HOST_RESTORE_DRILL_REQUIRED')
    else:
        try:
            completed = datetime.fromisoformat(drill['completed_at'])
            fresh = datetime.now(timezone.utc) - timedelta(hours=26) <= completed <= datetime.now(timezone.utc)
            valid = (fresh and drill['backup_sha256'] == drill['restored_sha256']
                     and bool(bucket) and drill['object_uri'].startswith(f's3://{bucket}/')
                     and drill['document_count'] > 0 and drill['event_count'] > 0
                     and release_at is not None and completed >= release_at)
        except (ValueError, TypeError):
            valid = False
        if not valid:
            blockers.append('OFF_HOST_RESTORE_DRILL_STALE_OR_INVALID')
    return {'ready_for_recurring_saas': not blockers, 'blockers': blockers,
            'ready_dossier_count': len(ready_ids), 'verified_customer_dossier_count': len(verified_at),
            'latest_recovery_drill_at': drill['completed_at'] if drill else None}
