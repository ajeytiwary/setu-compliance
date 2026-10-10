"""Synthetic fixtures exercise policy mechanics; they are not a real shipment."""
import copy
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import io
import json
from datetime import datetime, timedelta, timezone

import pytest

from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from app import db
from app.commercial_gate import assess
from app.recovery import backup_and_drill
from app.main import app
from app.pdf_observations import _geometry, _locate
from app.pilot_keys import mint_pilot_key

ROLES = ['INVOICE', 'PACKING_LIST', 'SHIPPING_BILL', 'BILL_OF_LADING',
         'MTC', 'IMPORT_DECLARATION', 'CBAM_INSTALLATION', 'VERIFICATION_OPINION']
VALUES = {
    'invoice_number': 'EXP/23-24/01244', 'cn_code': '72085120',
    'heat_number': 'CH-20376', 'net_weight_kg': '2252',
    'invoice_value': '12000', 'currency': 'USD', 'origin_country': 'INDIA',
    'container_number': 'TGHU6127284', 'bill_of_lading': 'SLDH00054055',
    'shipping_bill_number': '3331568', 'import_declaration_number': '26BE12345678',
    'installation_name': 'PLANTA', 'specific_embedded_emissions_tco2e_per_t': '2.5',
    'verification_status': 'VERIFIED', 'destination_country': 'BELGIUM',
    'production_route': 'C', 'reporting_year': '2026',
}
FIELDS_BY_ROLE = {
    'INVOICE': ['invoice_number', 'cn_code', 'net_weight_kg', 'invoice_value', 'currency', 'origin_country', 'destination_country', 'container_number'],
    'PACKING_LIST': ['invoice_number', 'net_weight_kg'],
    'SHIPPING_BILL': ['invoice_number', 'shipping_bill_number'],
    'BILL_OF_LADING': ['invoice_number', 'bill_of_lading', 'container_number'],
    'MTC': ['invoice_number', 'heat_number'],
    'IMPORT_DECLARATION': ['invoice_number', 'origin_country', 'destination_country', 'import_declaration_number'],
    'CBAM_INSTALLATION': ['invoice_number', 'cn_code', 'installation_name', 'specific_embedded_emissions_tco2e_per_t', 'production_route', 'reporting_year'],
    'VERIFICATION_OPINION': ['invoice_number', 'installation_name', 'verification_status'],
}


def _pdf(role):
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
    page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
    lines = [f'Synthetic test source {role}'] + [f'{field} {VALUES[field]}' for field in FIELDS_BY_ROLE[role]]
    parts = ['BT /F1 12 Tf 50 740 Td']
    for line in lines:
        parts.append(f'({line}) Tj 0 -22 Td')
    parts.append('ET')
    stream = DecodedStreamObject()
    stream.set_data('\n'.join(parts).encode())
    page[NameObject('/Contents')] = writer._add_object(stream)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def _headers(role, subject):
    token = mint_pilot_key('release-test', 'tenant-a', [role], 1, subject)
    return {'Authorization': 'Bearer ' + token, 'x-eurosetu-tenant': 'tenant-a'}


def test_release_requires_complete_reviewed_source_packet_and_invalidates_on_change(monkeypatch, tmp_path):
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'real.db')
    monkeypatch.setenv('EUROSETU_JWT_SECRET', 'release-test')
    monkeypatch.setenv('EUROSETU_ENV', 'production')
    monkeypatch.setenv('EUROSETU_DEPLOYMENT_TENANT', 'tenant-a')
    monkeypatch.setenv('EUROSETU_BACKUP_BUCKET', 'test-bucket')
    monkeypatch.delenv('EUROSETU_RECURRING_SAAS_ENABLED', raising=False)
    monkeypatch.delenv('DATABASE_URL', raising=False)
    contributor = _headers('pilot_contributor', 'author@example.test')
    verifier = _headers('verifier', 'reviewer@example.test')
    role_ids, pdfs = {}, {}
    with TestClient(app) as client:
        created = client.post('/api/real-dossiers', json={'name': 'Synthetic release policy fixture'}, headers=contributor)
        assert created.status_code == 201, created.text
        dossier_id = created.json()['dossier']['id']
        for role in ROLES:
            pdfs[role] = _pdf(role)
            response = client.post(f'/api/real-dossiers/{dossier_id}/documents',
                                   files={'file': (role.lower() + '.pdf', pdfs[role], 'application/pdf')},
                                   headers=contributor)
            assert response.status_code == 201, response.text
            role_ids[role] = response.json()['documents'][-1]['id']
        state = response.json()
        assert state['decision'] == 'BLOCKED'
        for document in state['documents']:
            response = client.post(f'/api/real-dossiers/{dossier_id}/documents/{document["id"]}/review',
                                   json={'approve': True, 'reason': 'Checked synthetic fixture source'}, headers=verifier)
            assert response.status_code == 200, response.text
        state = response.json()
        for edge in state['graph']['edges']:
            response = client.post(f'/api/real-dossiers/{dossier_id}/links/{edge["id"]}/review',
                                   json={'approve': True, 'reason': 'Shared invoice confirmed in source'}, headers=verifier)
            assert response.status_code == 200, response.text
        state = response.json()
        facts = []
        for role in ROLES:
            words = _geometry(pdfs[role])[0]
            for field in FIELDS_BY_ROLE[role]:
                raw = VALUES[field]
                bbox = _locate(words, raw)
                assert bbox, (role, field)
                facts.append({'field': field, 'value': raw, 'document_id': role_ids[role],
                              'source': {'page': 1, 'quote': raw, 'bbox': bbox}})
        invoice_index = next(i for i, f in enumerate(facts) if f['field'] == 'invoice_number' and f['document_id'] == role_ids['INVOICE'])
        links = [{'left': invoice_index, 'right': i} for i, fact in enumerate(facts)
                 if fact['field'] == 'invoice_number' and i != invoice_index]
        packet = {'source_kind': 'REAL_CLIENT_SHIPMENT',
                  'source_attestation': 'Test-only assertion that all documents describe one shipment.',
                  'roles': role_ids, 'facts': facts, 'links': links}
        from app import real_release
        conflicting = copy.deepcopy(packet)
        year_fact = next(f for f in conflicting['facts'] if f['field'] == 'reporting_year')
        conflicting['facts'].append({**year_fact, 'value': '2027'})
        with monkeypatch.context() as citation_stub:
            citation_stub.setattr(real_release, '_validate_citation', lambda *args: None)
            with pytest.raises(ValueError, match='FACT_VALUE_CONFLICT'):
                real_release.validate_packet(state, conflicting)
        for change, code in (
            (lambda p: p['roles'].pop('IMPORT_DECLARATION'), 'COMPLETE_SHIPMENT_ROLES_REQUIRED'),
            (lambda p: p['facts'][0]['source'].update(bbox=[0, 0, 612, 792]), 'BOUNDING_BOX_VALUE_MISMATCH'),
            (lambda p: p.update(source_kind='PUBLIC_EXAMPLE'), 'REAL_SOURCE_ATTESTATION_REQUIRED'),
            (lambda p: p.update(links=[]), 'EVIDENCE_GRAPH_INCOMPLETE'),
        ):
            rejected_packet = copy.deepcopy(packet)
            change(rejected_packet)
            rejected = client.post(f'/api/real-dossiers/{dossier_id}/release-packets',
                                   json={'packet': rejected_packet}, headers=contributor)
            assert rejected.status_code == 409, rejected.text
            assert rejected.json()['detail'] == code
        from app import cbam_definitive_v2
        with monkeypatch.context() as missing_reference:
            missing_reference.setattr(cbam_definitive_v2, 'free_allocation_adjustment',
                                      lambda *args, **kwargs: {'available': False, 'reason': 'BENCHMARK_NOT_FOUND'})
            blocked_calc = client.post(f'/api/real-dossiers/{dossier_id}/release-packets',
                                       json={'packet': packet}, headers=contributor)
            assert blocked_calc.status_code == 409
            assert blocked_calc.json()['detail'] == 'OFFICIAL_CBAM_BENCHMARK_OR_CSCF_REQUIRED'
        response = client.post(f'/api/real-dossiers/{dossier_id}/release-packets',
                               json={'packet': packet}, headers=contributor)
        assert response.status_code == 201, response.text
        packet_id = response.json()['packet_id']
        assert response.json()['state']['decision'] == 'BLOCKED'
        denied = client.post(f'/api/real-dossiers/{dossier_id}/release-packets/{packet_id}/review',
                             json={'approve': True, 'reason': 'Self approval'}, headers=contributor)
        assert denied.status_code == 403
        from app.real_release import decide
        barrier = Barrier(2)
        original_validate = real_release.validate_packet
        def concurrent_validate(*args):
            result = original_validate(*args)
            barrier.wait(timeout=20)
            return result
        def concurrent_review(reviewer):
            try:
                decide(dossier_id, 'tenant-a', packet_id, reviewer, True, 'Reviewed source citations and calculation')
                return 'APPROVED'
            except ValueError as exc:
                return str(exc)
        with monkeypatch.context() as concurrent:
            concurrent.setattr(real_release, 'validate_packet', concurrent_validate)
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(concurrent_review, ('reviewer@example.test', 'reviewer-2@example.test')))
        assert sorted(results) == ['APPROVED', 'RELEASE_ALREADY_DECIDED']
        response = client.get(f'/api/real-dossiers/{dossier_id}', headers=verifier)
        assert response.status_code == 200, response.text
        assert response.json()['decision'] == 'READY'
        assert len([event for event in response.json()['events'] if event['kind'] == 'release.decided']) == 1
        assert response.json()['release']['calculation']['embedded_emissions_tco2e'] == '5.6300'
        assert response.json()['release']['calculation']['certificate_obligation']['certificates_to_surrender_estimate'] > 0
        class MemoryStore:
            def __init__(self): self.objects = {}
            def put_object(self, **request): self.objects[(request['Bucket'],request['Key'])] = bytes(request['Body'])
            def get_object(self, **request): return {'Body': io.BytesIO(self.objects[(request['Bucket'],request['Key'])])}
        store = MemoryStore()
        backup_and_drill('tenant-a', 'test-bucket', 'tests', store)
        pre_signoff = assess('tenant-a')
        assert pre_signoff['ready_for_recurring_saas'] is False
        assert 'INDEPENDENT_CUSTOMER_SOURCE_SIGNOFF_REQUIRED' in pre_signoff['blockers']
        customer = _headers('customer_signatory', 'customer@example.test')
        administrator = _headers('admin', 'independent-admin@example.test')
        source_response = client.post(f'/api/real-dossiers/{dossier_id}/source-signoffs',
                                      data={'customer_name': 'Example Steel Importer', 'shipment_reference': VALUES['invoice_number'],
                                            'reason': 'I confirm these original shipment records belong to our company and may be reviewed.'},
                                      files={'consent_pdf': ('signed-consent.pdf', _pdf('INVOICE'), 'application/pdf')},
                                      headers=customer)
        assert source_response.status_code == 201, source_response.text
        signoff_id = source_response.json()['signoff_id']
        consent_path = f'/api/real-dossiers/{dossier_id}/source-signoffs/{signoff_id}/consent'
        assert client.get(consent_path, headers=customer).status_code == 403
        retrieved_consent = client.get(consent_path, headers=administrator)
        assert retrieved_consent.status_code == 200
        assert retrieved_consent.content == _pdf('INVOICE')
        assert retrieved_consent.headers['cache-control'] == 'no-store'
        denied_source_review = client.post(f'/api/real-dossiers/{dossier_id}/source-signoffs/{signoff_id}/review',
                                           json={'approve': True, 'reason': 'Not an administrator'}, headers=customer)
        assert denied_source_review.status_code == 403
        source_review = client.post(f'/api/real-dossiers/{dossier_id}/source-signoffs/{signoff_id}/review',
                                    json={'approve': True, 'reason': 'Independently checked customer identity and signed consent'},
                                    headers=administrator)
        assert source_review.status_code == 200, source_review.text
        assert assess('tenant-a')['ready_for_recurring_saas'] is False  # drill preceded signoff
        backup_and_drill('tenant-a', 'test-bucket', 'tests', store)
        assert assess('tenant-a')['ready_for_recurring_saas'] is True
        monkeypatch.setenv('EUROSETU_RECURRING_SAAS_ENABLED', '1')
        assert client.get('/health/ready').status_code == 200
        with db.connect() as conn:
            original_drills = [tuple(row) for row in conn.execute('SELECT id,completed_at FROM recovery_drills')]
            conn.execute('UPDATE recovery_drills SET completed_at=?',
                         ((datetime.now(timezone.utc) - timedelta(hours=27)).isoformat(),))
        assert client.get('/health/ready').status_code == 503
        blocked_write = client.post('/api/real-dossiers', json={'name': 'Unprotected new upload'}, headers=contributor)
        assert blocked_write.status_code == 503
        assert client.get(f'/api/real-dossiers/{dossier_id}', headers=contributor).status_code == 200
        with db.connect() as conn:
            for drill_id, completed_at in original_drills:
                conn.execute('UPDATE recovery_drills SET completed_at=? WHERE id=?', (completed_at, drill_id))
        assert client.get('/health/ready').status_code == 200
        with db.connect() as conn:
            original_signoff_time = conn.execute('SELECT reviewed_at FROM real_source_signoffs WHERE id=?', (signoff_id,)).fetchone()[0]
            conn.execute('UPDATE real_source_signoffs SET reviewed_at=? WHERE id=?', ('2020-01-01T00:00:00+00:00', signoff_id))
        assert assess('tenant-a')['ready_for_recurring_saas'] is False
        assert client.get('/health/ready').status_code == 503
        with db.connect() as conn:
            conn.execute('UPDATE real_source_signoffs SET reviewed_at=? WHERE id=?', (original_signoff_time, signoff_id))
            original_release_time = conn.execute('SELECT reviewed_at FROM real_release_packets WHERE id=?', (packet_id,)).fetchone()[0]
            conn.execute('UPDATE real_release_packets SET reviewed_at=? WHERE id=?', ('2020-01-01T00:00:00+00:00', packet_id))
        assert assess('tenant-a')['ready_for_recurring_saas'] is False
        with db.connect() as conn:
            conn.execute('UPDATE real_release_packets SET reviewed_at=? WHERE id=?', (original_release_time, packet_id))
            original_consent = conn.execute('SELECT consent_pdf FROM real_source_signoffs WHERE id=?', (signoff_id,)).fetchone()[0]
            conn.execute('UPDATE real_source_signoffs SET consent_pdf=? WHERE id=?', (b'%PDF-tampered', signoff_id))
        assert assess('tenant-a')['ready_for_recurring_saas'] is False
        with db.connect() as conn:
            conn.execute('UPDATE real_source_signoffs SET consent_pdf=? WHERE id=?', (original_consent, signoff_id))
        assert assess('tenant-a')['ready_for_recurring_saas'] is True
        from app import real_release
        with monkeypatch.context() as revised_reference:
            revised_reference.setattr(real_release, '_reference_snapshots', lambda: {'benchmarks.json': 'changed', 'cscf.json': 'changed'})
            regulatory_change = client.get(f'/api/real-dossiers/{dossier_id}', headers=verifier).json()
            assert regulatory_change['decision'] == 'BLOCKED'
            assert 'RELEASE_INVALID_OR_STALE' in regulatory_change['blockers']
            assert assess('tenant-a')['ready_for_recurring_saas'] is False
        with db.connect() as conn:
            original_hash = conn.execute('SELECT decision_hash FROM real_release_packets WHERE id=?', (packet_id,)).fetchone()[0]
            altered = copy.deepcopy(packet)
            altered['source_attestation'] += ' altered after review'
            conn.execute('UPDATE real_release_packets SET packet_json=? WHERE id=?', (json.dumps(altered), packet_id))
        tampered_packet = client.get(f'/api/real-dossiers/{dossier_id}', headers=verifier).json()
        assert tampered_packet['decision'] == 'BLOCKED'
        with db.connect() as conn:
            conn.execute('UPDATE real_release_packets SET packet_json=? WHERE id=?', (json.dumps(packet), packet_id))
            conn.execute('UPDATE real_release_packets SET decision_hash=? WHERE id=?', ('tampered', packet_id))
        response = client.get(f'/api/real-dossiers/{dossier_id}', headers=verifier)
        assert response.json()['decision'] == 'BLOCKED'
        assert 'RELEASE_INVALID_OR_STALE' in response.json()['blockers']
        assert assess('tenant-a')['ready_for_recurring_saas'] is False
        with db.connect() as conn:
            conn.execute('UPDATE real_release_packets SET decision_hash=? WHERE id=?', (original_hash, packet_id))
        changed = client.post(f'/api/real-dossiers/{dossier_id}/documents',
                              files={'file': ('new-source.pdf', _pdf('INVOICE') + b'\n', 'application/pdf')},
                              headers=contributor)
        assert changed.status_code == 201, changed.text
        assert changed.json()['decision'] == 'BLOCKED'
        assert 'RELEASE_INVALID_OR_STALE' in changed.json()['blockers']
        assert assess('tenant-a')['ready_for_recurring_saas'] is False
