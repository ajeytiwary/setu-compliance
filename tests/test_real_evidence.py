import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import db
from app.main import app
from app.pilot_keys import mint_pilot_key


def _headers(subject,role,tenant='tenant-a'):
    token=mint_pilot_key('real-evidence-test',tenant,[role],1,subject)
    return {'Authorization':'Bearer '+token,'x-eurosetu-tenant':tenant}


def _corpus():
    path=os.getenv('EUROSETU_PUBLIC_CORPUS_DIR')
    if not path:pytest.skip('Set EUROSETU_PUBLIC_CORPUS_DIR to run public PDF integration tests')
    return Path(path)


def test_real_pdf_upload_graph_review_and_tamper(monkeypatch,tmp_path):
    corpus=_corpus()
    monkeypatch.setattr(db,'DB_PATH',tmp_path/'real.db')
    monkeypatch.setenv('EUROSETU_JWT_SECRET','real-evidence-test')
    con=_headers('contributor@example.test','pilot_contributor')
    ver=_headers('verifier@example.test','verifier')
    other=_headers('viewer@example.test','pilot_viewer','tenant-b')
    with TestClient(app) as client:
        created=client.post('/api/real-dossiers',json={'name':'Public source test'},headers=con)
        assert created.status_code==201,created.text
        did=created.json()['dossier']['id']
        for sid in ('975352350','975352352','574284615'):
            path=corpus/f'scribd-{sid}.pdf'
            response=client.post(f'/api/real-dossiers/{did}/documents',files={'file':(path.name,path.read_bytes(),'application/pdf')},headers=con)
            assert response.status_code==201,response.text
        state=response.json()
        assert len(state['graph']['nodes'])==3
        assert len(state['graph']['edges'])==1
        assert state['graph']['conflicts'][0]['field']=='net_weight_kg'
        assert state['decision']=='BLOCKED'
        assert state['integrity']=={'sources':True,'audit_chain':True,'reviews':True}
        assert client.get(f'/api/real-dossiers/{did}',headers=other).status_code==404
        for doc in state['documents']:
            file=client.get(f'/api/real-dossiers/{did}/documents/{doc["id"]}/file',headers=ver)
            assert file.status_code==200
            assert client.post(f'/api/real-dossiers/{did}/documents/{doc["id"]}/review',json={'approve':True,'reason':'self'},headers=con).status_code==403
            reviewed=client.post(f'/api/real-dossiers/{did}/documents/{doc["id"]}/review',json={'approve':True,'reason':'Source checked'},headers=ver)
            assert reviewed.status_code==200,reviewed.text
        state=reviewed.json()
        assert state['decision']=='BLOCKED'
        assert 'COMPLETE_EU_SHIPMENT_AND_VERIFIED_CBAM_NOT_ESTABLISHED' in state['blockers']
        edge=state['graph']['edges'][0]
        assert edge['status']=='CANDIDATE_REQUIRES_LINK_REVIEW'
        approval=client.post(f'/api/real-dossiers/{did}/links/{edge["id"]}/review',json={'approve':True,'reason':'Invoice and container match'},headers=ver)
        assert approval.status_code==409 and approval.json()['detail']=='UNRESOLVED_SOURCE_CONFLICT'
        rejection=client.post(f'/api/real-dossiers/{did}/links/{edge["id"]}/review',json={'approve':False,'reason':'0.01 kg discrepancy'},headers=ver)
        assert rejection.status_code==200
        assert rejection.json()['graph']['edges'][0]['status']=='REJECTED'
        with db.connect() as conn:
            conn.execute('UPDATE real_link_reviews SET status=? WHERE dossier_id=? AND edge_id=?',('APPROVED',did,edge['id']))
        forged_link=client.get(f'/api/real-dossiers/{did}',headers=ver).json()
        assert forged_link['integrity']['reviews'] is False
        assert 'REVIEW_AUDIT_MISMATCH' in forged_link['blockers']
        with db.connect() as conn:
            conn.execute('UPDATE real_link_reviews SET status=? WHERE dossier_id=? AND edge_id=?',('REJECTED',did,edge['id']))
        with db.connect() as conn:
            conn.execute('UPDATE real_documents SET parsed_json=? WHERE id=?',('{}',state['documents'][0]['id']))
        tampered=client.get(f'/api/real-dossiers/{did}',headers=ver).json()
        assert tampered['integrity']['sources'] is False
        assert 'SOURCE_INTEGRITY_FAILED' in tampered['blockers']


def test_public_selected_gold_and_negative_link():
    corpus=_corpus()
    from scripts.evaluate_public_corpus import evaluate
    score=evaluate(corpus)
    assert score['field_hits']==38
    assert score['field_total']==38
    assert score['row_cell_hits']==12
    assert score['row_cell_total']==12
    assert score['expected_positive_link_present']
    assert score['expected_negative_link_absent']
    assert score['weight_conflict_detected']
