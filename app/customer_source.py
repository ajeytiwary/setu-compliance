"""Independent customer-origin signoff bound to one reviewed real dossier."""
from __future__ import annotations

import hashlib
from uuid import uuid4

from .real_evidence import _connect, _event, _now, _owned, get
from .real_release import _hash, evidence_fingerprint

SCHEMA = '''
CREATE TABLE IF NOT EXISTS real_source_signoffs (
 id TEXT PRIMARY KEY, dossier_id TEXT NOT NULL REFERENCES real_dossiers(id), tenant_id TEXT NOT NULL,
 packet_id TEXT NOT NULL REFERENCES real_release_packets(id), customer_name TEXT NOT NULL,
 shipment_reference TEXT NOT NULL, consent_pdf BLOB NOT NULL, consent_sha256 TEXT NOT NULL,
 evidence_hash TEXT NOT NULL, signatory TEXT NOT NULL, signatory_reason TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('PENDING','APPROVED','REJECTED')),
 reviewer TEXT, review_reason TEXT, decision_hash TEXT, created_at TEXT NOT NULL, reviewed_at TEXT);
CREATE INDEX IF NOT EXISTS idx_real_source_signoffs_dossier ON real_source_signoffs(dossier_id,created_at);
CREATE INDEX IF NOT EXISTS idx_real_source_signoffs_tenant_status ON real_source_signoffs(tenant_id,status,dossier_id);
'''


def _db():
    conn = _connect()
    conn.executescript(SCHEMA)
    return conn


def submit(dossier_id: str, tenant_id: str, actor: str, customer_name: str,
           shipment_reference: str, reason: str, consent_pdf: bytes) -> str:
    if not customer_name.strip() or not shipment_reference.strip() or len(customer_name) > 200 or len(shipment_reference) > 120:
        raise ValueError('CUSTOMER_AND_SHIPMENT_REQUIRED')
    if len(reason.strip()) < 30 or len(reason) > 1000:
        raise ValueError('CUSTOMER_SOURCE_ASSERTION_REQUIRED')
    if not consent_pdf.startswith(b'%PDF-') or len(consent_pdf) > 8 * 1024 * 1024:
        raise ValueError('SIGNED_CONSENT_PDF_REQUIRED')
    state = get(dossier_id, tenant_id)
    if state['decision'] != 'READY' or not state.get('release'):
        raise ValueError('REVIEWED_READY_DOSSIER_REQUIRED')
    signoff_id = str(uuid4())
    consent_hash = hashlib.sha256(consent_pdf).hexdigest()
    fingerprint = evidence_fingerprint(state)
    packet_id = state['release']['id']
    with _db() as conn:
        conn.execute('BEGIN IMMEDIATE')
        _owned(conn, dossier_id, tenant_id)
        conn.execute('INSERT INTO real_source_signoffs(id,dossier_id,tenant_id,packet_id,customer_name,shipment_reference,consent_pdf,consent_sha256,evidence_hash,signatory,signatory_reason,status,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                     (signoff_id,dossier_id,tenant_id,packet_id,customer_name.strip(),shipment_reference.strip(),consent_pdf,consent_hash,fingerprint,actor,reason.strip(),'PENDING',_now()))
        _event(conn,dossier_id,actor,'source_signoff.submitted',{'signoff_id':signoff_id,'packet_id':packet_id,'consent_sha256':consent_hash,'evidence_hash':fingerprint})
        conn.commit()
    return signoff_id


def decide(dossier_id: str, tenant_id: str, signoff_id: str, actor: str, approve: bool, reason: str) -> None:
    if len(reason.strip()) < 20 or len(reason) > 1000:
        raise ValueError('SOURCE_REVIEW_REASON_REQUIRED')
    state = get(dossier_id, tenant_id)
    with _db() as conn:
        row = conn.execute('SELECT * FROM real_source_signoffs WHERE id=? AND dossier_id=? AND tenant_id=?',
                           (signoff_id,dossier_id,tenant_id)).fetchone()
        if row is None:
            raise KeyError('SOURCE_SIGNOFF_NOT_FOUND')
        if row['status'] != 'PENDING':
            raise ValueError('SOURCE_SIGNOFF_ALREADY_DECIDED')
        if actor in ({row['signatory'],state['release']['submitted_by'],state['release']['reviewer']}
                     | {d['uploaded_by'] for d in state['documents']}):
            raise ValueError('SOURCE_REVIEWER_MUST_BE_INDEPENDENT')
        if state['decision'] != 'READY' or state['release']['id'] != row['packet_id'] or evidence_fingerprint(state) != row['evidence_hash']:
            raise ValueError('RELEASE_SOURCE_CHANGED')
        if hashlib.sha256(bytes(row['consent_pdf'])).hexdigest() != row['consent_sha256']:
            raise ValueError('CONSENT_SOURCE_INTEGRITY_FAILED')
        status = 'APPROVED' if approve else 'REJECTED'
        reviewed_at = _now()
        decision_hash = _hash({'signoff_id':signoff_id,'packet_id':row['packet_id'],'consent_sha256':row['consent_sha256'],
                               'evidence_hash':row['evidence_hash'],'customer_name':row['customer_name'],
                               'shipment_reference':row['shipment_reference'],'signatory':row['signatory'],
                               'signatory_reason':row['signatory_reason'],'status':status,'reviewer':actor,
                               'reason':reason.strip(),'reviewed_at':reviewed_at})
        conn.execute('BEGIN IMMEDIATE')
        updated = conn.execute('UPDATE real_source_signoffs SET status=?,reviewer=?,review_reason=?,decision_hash=?,reviewed_at=? WHERE id=? AND status=?',
                               (status,actor,reason.strip(),decision_hash,reviewed_at,signoff_id,'PENDING'))
        if updated.rowcount != 1:
            raise ValueError('SOURCE_SIGNOFF_ALREADY_DECIDED')
        _event(conn,dossier_id,actor,'source_signoff.decided',{'signoff_id':signoff_id,'status':status,'decision_hash':decision_hash})
        conn.commit()


def approved_at_for(state: dict) -> str | None:
    if state['decision'] != 'READY' or not state.get('release') or not all(state['integrity'].values()):
        return None
    dossier_id, tenant_id = state['dossier']['id'], state['dossier']['tenant_id']
    with _db() as conn:
        rows = conn.execute("SELECT * FROM real_source_signoffs WHERE dossier_id=? AND tenant_id=? AND status='APPROVED' ORDER BY rowid DESC",
                            (dossier_id,tenant_id)).fetchall()
    for row in rows:
        if row['packet_id'] != state['release']['id'] or row['evidence_hash'] != evidence_fingerprint(state):
            continue
        if hashlib.sha256(bytes(row['consent_pdf'])).hexdigest() != row['consent_sha256']:
            continue
        expected = _hash({'signoff_id':row['id'],'packet_id':row['packet_id'],'consent_sha256':row['consent_sha256'],
                          'evidence_hash':row['evidence_hash'],'customer_name':row['customer_name'],
                          'shipment_reference':row['shipment_reference'],'signatory':row['signatory'],
                          'signatory_reason':row['signatory_reason'],'status':row['status'],
                          'reviewer':row['reviewer'],'reason':row['review_reason'],'reviewed_at':row['reviewed_at']})
        if row['decision_hash'] != expected:
            continue
        submitted = [e for e in state['events'] if e['kind'] == 'source_signoff.submitted' and e['payload'].get('signoff_id') == row['id']]
        decided = [e for e in state['events'] if e['kind'] == 'source_signoff.decided' and e['payload'].get('signoff_id') == row['id']]
        if (len(submitted) == len(decided) == 1
                and submitted[0]['actor'] == row['signatory']
                and submitted[0]['payload'].get('packet_id') == row['packet_id']
                and submitted[0]['payload'].get('consent_sha256') == row['consent_sha256']
                and submitted[0]['payload'].get('evidence_hash') == row['evidence_hash']
                and decided[0]['actor'] == row['reviewer']
                and decided[0]['payload'].get('status') == 'APPROVED'
                and decided[0]['payload'].get('decision_hash') == expected
                and row['reviewer'] != row['signatory']):
            return row['reviewed_at']
    return None


def consent_bytes(dossier_id: str, tenant_id: str, signoff_id: str) -> bytes:
    with _db() as conn:
        _owned(conn, dossier_id, tenant_id)
        row = conn.execute('SELECT consent_pdf,consent_sha256 FROM real_source_signoffs WHERE id=? AND dossier_id=? AND tenant_id=?',
                           (signoff_id,dossier_id,tenant_id)).fetchone()
        if row is None:
            raise KeyError('SOURCE_SIGNOFF_NOT_FOUND')
        data = bytes(row['consent_pdf'])
        if hashlib.sha256(data).hexdigest() != row['consent_sha256']:
            raise ValueError('CONSENT_SOURCE_INTEGRITY_FAILED')
        return data
