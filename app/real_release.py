"""Audited release packets for real steel shipments.

A packet is a reviewer-authored mapping from source documents to one shipment.
Its READY result is an internal evidence decision, never a customs filing or
independent emissions verification.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import subprocess
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from .real_evidence import _connect, _event, _now, _owned

REQUIRED_ROLES = frozenset({
    'INVOICE', 'PACKING_LIST', 'SHIPPING_BILL', 'BILL_OF_LADING', 'MTC',
    'IMPORT_DECLARATION', 'CBAM_INSTALLATION', 'VERIFICATION_OPINION',
})
REQUIRED_FACTS = frozenset({
    'invoice_number', 'cn_code', 'heat_number', 'net_weight_kg',
    'invoice_value', 'currency', 'origin_country', 'container_number',
    'bill_of_lading', 'shipping_bill_number', 'import_declaration_number',
    'installation_name', 'specific_embedded_emissions_tco2e_per_t',
    'verification_status', 'destination_country', 'production_route', 'reporting_year',
})
JOIN_FIELDS = frozenset({
    'invoice_number', 'container_number', 'bill_of_lading', 'heat_number',
    'shipping_bill_number', 'import_declaration_number', 'installation_name',
})
SCHEMA = '''
CREATE TABLE IF NOT EXISTS real_release_packets (
 id TEXT PRIMARY KEY, dossier_id TEXT NOT NULL REFERENCES real_dossiers(id),
 tenant_id TEXT NOT NULL, submitted_by TEXT NOT NULL, packet_json TEXT NOT NULL,
 packet_hash TEXT NOT NULL, evidence_hash TEXT NOT NULL, calculation_json TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('PENDING','APPROVED','REJECTED')),
 reviewer TEXT, review_reason TEXT, decision_hash TEXT, created_at TEXT NOT NULL,
 reviewed_at TEXT);
CREATE INDEX IF NOT EXISTS idx_real_release_dossier ON real_release_packets(dossier_id,created_at);
'''


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), default=str)


def _hash(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _norm(value: object) -> str:
    return re.sub(r'\s+', ' ', str(value).strip()).casefold()


EU_COUNTRIES = {
    'AT': 'AUSTRIA', 'BE': 'BELGIUM', 'BG': 'BULGARIA', 'HR': 'CROATIA',
    'CY': 'CYPRUS', 'CZ': 'CZECHIA', 'DK': 'DENMARK', 'EE': 'ESTONIA',
    'FI': 'FINLAND', 'FR': 'FRANCE', 'DE': 'GERMANY', 'GR': 'GREECE',
    'HU': 'HUNGARY', 'IE': 'IRELAND', 'IT': 'ITALY', 'LV': 'LATVIA',
    'LT': 'LITHUANIA', 'LU': 'LUXEMBOURG', 'MT': 'MALTA', 'NL': 'NETHERLANDS',
    'PL': 'POLAND', 'PT': 'PORTUGAL', 'RO': 'ROMANIA', 'SK': 'SLOVAKIA',
    'SI': 'SLOVENIA', 'ES': 'SPAIN', 'SE': 'SWEDEN',
}


def _typed_value(field: str, value: object) -> str:
    if field in {'net_weight_kg', 'invoice_value', 'specific_embedded_emissions_tco2e_per_t'}:
        try:
            number = Decimal(str(value).replace(',', '').strip())
            if not number.is_finite():
                raise InvalidOperation()
            return str(number.normalize())
        except InvalidOperation:
            raise ValueError('INVALID_NUMERIC_FACT')
    if field in {'origin_country', 'destination_country'}:
        country = str(value).strip().upper()
        return {'IN': 'INDIA', 'CZECH REPUBLIC': 'CZECHIA'}.get(country, EU_COUNTRIES.get(country, country)).casefold()
    if field == 'cn_code':
        digits = re.sub(r'\D', '', str(value))
        if len(digits) != 8:
            raise ValueError('INVALID_EU_CN_CODE')
        return digits
    return _norm(value)


def _reference_snapshots() -> dict:
    from .cbam_definitive_v2 import DATA
    out = {}
    for name in ('benchmarks.json', 'cscf.json'):
        path = DATA / name
        if not path.is_file():
            raise ValueError('OFFICIAL_CBAM_REFERENCE_SNAPSHOT_MISSING')
        out[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def evidence_fingerprint(state: dict) -> str:
    return _hash({
        'dossier_id': state['dossier']['id'],
        'documents': sorted((d['id'], d['sha256'], d['role'], d['review_status'],
                             d['reviewed_by'], d['reviewed_at']) for d in state['documents']),
        'edges': sorted((e['id'], e['status'], e['reviewed_by']) for e in state['graph']['edges']),
        'conflicts': state['graph']['conflicts'],
    })


def _bbox_matches(words: list[dict], value: str, supplied: list) -> bool:
    target = re.sub(r'[^A-Z0-9]', '', value.upper())
    if not target:
        return False
    for i in range(len(words)):
        joined = ''
        first_y = words[i]['bbox'][1]
        for j in range(i, min(i + 30, len(words))):
            if abs(words[j]['bbox'][1] - first_y) > 4:
                break
            joined += re.sub(r'[^A-Z0-9]', '', words[j]['text'].upper())
            if joined == target:
                actual = [min(w['bbox'][0] for w in words[i:j + 1]),
                          min(w['bbox'][1] for w in words[i:j + 1]),
                          max(w['bbox'][2] for w in words[i:j + 1]),
                          max(w['bbox'][3] for w in words[i:j + 1])]
                if all(abs(float(supplied[k]) - actual[k]) <= 3 for k in range(4)):
                    return True
                break
            if len(joined) > len(target):
                break
    return False


def _source_text(data: bytes, page: int) -> str:
    result = subprocess.run(['pdftotext', '-f', str(page), '-l', str(page), '-', '-'],
                            input=data, capture_output=True, timeout=15, check=False)
    if result.returncode:
        raise ValueError('CITATION_SOURCE_UNREADABLE')
    return _norm(result.stdout.decode('utf-8', 'replace'))


def _validate_citation(fact: dict, data: bytes, filename: str, cache: dict) -> None:
    value = str(fact.get('value') or '').strip()
    if not value or len(value) > 200:
        raise ValueError('FACT_VALUE_REQUIRED')
    source = fact.get('source') or {}
    if not isinstance(source, dict):
        raise ValueError('INVALID_FACT_SOURCE')
    if filename.lower().endswith('.pdf'):
        import pypdf
        page = source.get('page')
        bbox = source.get('bbox')
        quote = str(source.get('quote') or '').strip()
        if len(quote) > 500:
            raise ValueError('SOURCE_QUOTE_TOO_LONG')
        if type(page) is not int or page < 1 or not quote or not isinstance(bbox, list) or len(bbox) != 4:
            raise ValueError('PDF_PAGE_QUOTE_BBOX_REQUIRED')
        reader = cache.get(('pdf', fact['document_id']))
        if reader is None:
            reader = pypdf.PdfReader(io.BytesIO(data))
            cache[('pdf', fact['document_id'])] = reader
        if page > len(reader.pages):
            raise ValueError('CITATION_PAGE_OUT_OF_RANGE')
        width, height = float(reader.pages[page - 1].mediabox.width), float(reader.pages[page - 1].mediabox.height)
        if not all(type(x) in (int, float) and x >= 0 for x in bbox):
            raise ValueError('INVALID_SOURCE_BBOX')
        x0, y0, x1, y1 = bbox
        if x0 >= x1 or y0 >= y1 or x1 > width or y1 > height:
            raise ValueError('INVALID_SOURCE_BBOX')
        from .pdf_observations import _geometry
        geometry = cache.get(('geometry', fact['document_id']))
        if geometry is None:
            geometry = _geometry(data)
            cache[('geometry', fact['document_id'])] = geometry
        if page > len(geometry) or not _bbox_matches(geometry[page - 1], value, bbox):
            raise ValueError('BOUNDING_BOX_VALUE_MISMATCH')
        if _norm(value) not in _norm(quote):
            raise ValueError('FACT_NOT_IN_QUOTE')
        text = cache.get(('text', fact['document_id'], page))
        if text is None:
            text = _source_text(data, page)
            cache[('text', fact['document_id'], page)] = text
        if _norm(quote) not in text:
            raise ValueError('QUOTE_NOT_ON_SOURCE_PAGE')
    elif filename.lower().endswith('.xlsx'):
        import openpyxl
        sheet, cell = source.get('sheet'), source.get('cell')
        if not isinstance(sheet, str) or not isinstance(cell, str) or not re.fullmatch(r'[A-Z]{1,3}[1-9]\d{0,5}', cell):
            raise ValueError('WORKBOOK_SHEET_CELL_REQUIRED')
        workbook = cache.get(('xlsx', fact['document_id']))
        if workbook is None:
            workbook = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
            cache[('xlsx', fact['document_id'])] = workbook
        if sheet not in workbook.sheetnames or _norm(workbook[sheet][cell].value) != _norm(value):
            raise ValueError('WORKBOOK_CELL_MISMATCH')
    else:
        raise ValueError('UNSUPPORTED_SOURCE_TYPE')


def validate_packet(state: dict, packet: dict) -> dict:
    if len(_canonical(packet).encode()) > 256_000:
        raise ValueError('RELEASE_PACKET_TOO_LARGE')
    if any(not ok for ok in state['integrity'].values()):
        raise ValueError('DOSSIER_INTEGRITY_FAILED')
    if state['graph']['conflicts']:
        raise ValueError('UNRESOLVED_SOURCE_CONFLICT')
    if any(e['status'] != 'APPROVED' for e in state['graph']['edges']):
        raise ValueError('LINK_REVIEW_REQUIRED')
    docs = {d['id']: d for d in state['documents']}
    if not docs or any(d['review_status'] != 'APPROVED' for d in docs.values()):
        raise ValueError('DOCUMENT_REVIEW_REQUIRED')
    roles = packet.get('roles')
    if not isinstance(roles, dict) or set(roles) != REQUIRED_ROLES or any(not isinstance(v, str) for v in roles.values()) or len(set(roles.values())) != len(roles):
        raise ValueError('COMPLETE_SHIPMENT_ROLES_REQUIRED')
    if packet.get('source_kind') != 'REAL_CLIENT_SHIPMENT' or not isinstance(packet.get('source_attestation'), str) or len(packet['source_attestation'].strip()) < 30:
        raise ValueError('REAL_SOURCE_ATTESTATION_REQUIRED')
    if set(roles.values()) != set(docs):
        raise ValueError('UNRELATED_OR_MISSING_DOCUMENT')
    # A blank form or educational case cannot become an actual customs entry.
    prohibited = {'SAD_CASE_STUDY', 'BLANK_IMPORT_FORM'}
    if any(d['parsed'].get('role') in prohibited for d in docs.values()):
        raise ValueError('EDUCATIONAL_OR_BLANK_SOURCE')
    facts = packet.get('facts')
    if not isinstance(facts, list) or len(facts) > 100 or not REQUIRED_FACTS.issubset({f.get('field') for f in facts if isinstance(f, dict)}):
        raise ValueError('CRITICAL_FACTS_MISSING')
    by_role = {doc_id: role for role, doc_id in roles.items()}
    role_requirements = {
        'invoice_number': 'INVOICE', 'invoice_value': 'INVOICE', 'currency': 'INVOICE',
        'heat_number': 'MTC', 'shipping_bill_number': 'SHIPPING_BILL',
        'bill_of_lading': 'BILL_OF_LADING', 'import_declaration_number': 'IMPORT_DECLARATION',
        'installation_name': 'CBAM_INSTALLATION',
        'specific_embedded_emissions_tco2e_per_t': 'CBAM_INSTALLATION',
        'verification_status': 'VERIFICATION_OPINION',
        'production_route': 'CBAM_INSTALLATION', 'reporting_year': 'CBAM_INSTALLATION',
    }
    from .real_evidence import document_bytes
    cache = {}
    for fact in facts:
        if not isinstance(fact, dict) or fact.get('document_id') not in docs or not isinstance(fact.get('field'), str):
            raise ValueError('INVALID_FACT_SOURCE')
        field = fact['field']
        if field in role_requirements and not any(
            f.get('field') == field and by_role.get(f.get('document_id')) == role_requirements[field]
            for f in facts if isinstance(f, dict)
        ):
            raise ValueError('FACT_WRONG_DOCUMENT_ROLE')
        source_document = cache.get(('blob', fact['document_id']))
        if source_document is None:
            source_document = document_bytes(state['dossier']['id'], state['dossier']['tenant_id'], fact['document_id'])
            cache[('blob', fact['document_id'])] = source_document
        data, filename = source_document
        _validate_citation(fact, data, filename, cache)
    for field in role_requirements:
        if not any(f['field'] == field and by_role[f['document_id']] == role_requirements[field] for f in facts):
            raise ValueError('FACT_WRONG_DOCUMENT_ROLE')
    for field, required_roles in {'cn_code': {'INVOICE', 'CBAM_INSTALLATION'},
                                  'net_weight_kg': {'INVOICE', 'PACKING_LIST'},
                                  'origin_country': {'INVOICE', 'IMPORT_DECLARATION'},
                                  'destination_country': {'INVOICE', 'IMPORT_DECLARATION'}}.items():
        present = {by_role[f['document_id']] for f in facts if f['field'] == field}
        if not required_roles.issubset(present):
            raise ValueError('CROSS_DOCUMENT_FACT_REQUIRED')
    by_field = {}
    for fact in facts:
        by_field.setdefault(fact['field'], set()).add(_typed_value(fact['field'], fact['value']))
    for field in REQUIRED_FACTS:
        if len(by_field.get(field, set())) != 1:
            raise ValueError('FACT_VALUE_CONFLICT')
    if by_field['origin_country'] != {'india'}:
        raise ValueError('INDIAN_ORIGIN_REQUIRED')
    if len(by_field['destination_country']) != 1 or next(iter(by_field['destination_country'])) not in {v.casefold() for v in EU_COUNTRIES.values()}:
        raise ValueError('EU_DESTINATION_REQUIRED')
    from .pdf_observations import _valid_container
    if not _valid_container(next(iter(by_field['container_number'])).upper()):
        raise ValueError('INVALID_CONTAINER_NUMBER')
    if Decimal(next(iter(by_field['invoice_value']))) <= 0:
        raise ValueError('INVALID_INVOICE_VALUE')
    if not re.fullmatch(r'[A-Z]{3}', str(next(f['value'] for f in facts if f['field'] == 'currency'))):
        raise ValueError('INVALID_CURRENCY')
    if by_field['verification_status'] != {'verified'}:
        raise ValueError('CBAM_VERIFICATION_REQUIRED')
    if len({f['document_id'] for f in facts if f['field'] == 'invoice_number'}) < 2:
        raise ValueError('INVOICE_CROSS_DOCUMENT_CONFIRMATION_REQUIRED')
    if len({f['document_id'] for f in facts if f['field'] == 'net_weight_kg'}) < 2:
        raise ValueError('WEIGHT_CROSS_DOCUMENT_CONFIRMATION_REQUIRED')
    links = packet.get('links')
    if not isinstance(links, list) or len(links) < len(docs) - 1 or len(links) > 100:
        raise ValueError('EVIDENCE_GRAPH_INCOMPLETE')
    connected = {roles['INVOICE']}
    accepted = set()
    for link in links:
        if not isinstance(link, dict) or type(link.get('left')) is not int or type(link.get('right')) is not int:
            raise ValueError('INVALID_EVIDENCE_LINK')
        left, right = link['left'], link['right']
        if min(left, right) < 0 or max(left, right) >= len(facts):
            raise ValueError('INVALID_EVIDENCE_LINK')
        a, b = facts[left], facts[right]
        if a['document_id'] == b['document_id'] or a['field'] != b['field'] or a['field'] not in JOIN_FIELDS or _norm(a['value']) != _norm(b['value']):
            raise ValueError('UNSUPPORTED_EVIDENCE_LINK')
        accepted.add(frozenset((a['document_id'], b['document_id'])))
    while True:
        expanded = connected | {item for edge in accepted if edge & connected for item in edge}
        if expanded == connected:
            break
        connected = expanded
    if connected != set(docs):
        raise ValueError('EVIDENCE_GRAPH_DISCONNECTED')
    try:
        weight = Decimal(str(next(f['value'] for f in facts if f['field'] == 'net_weight_kg')).replace(',', ''))
        intensity = Decimal(str(next(f['value'] for f in facts if f['field'] == 'specific_embedded_emissions_tco2e_per_t')).replace(',', ''))
        if not weight.is_finite() or not intensity.is_finite() or weight <= 0 or intensity < 0:
            raise InvalidOperation()
    except (InvalidOperation, ValueError):
        raise ValueError('INVALID_CALCULATION_INPUT')
    from .cbam_definitive_v2 import certificate_obligation, free_allocation_adjustment
    try:
        year = int(next(f['value'] for f in facts if f['field'] == 'reporting_year'))
    except (TypeError, ValueError):
        raise ValueError('INVALID_REPORTING_YEAR')
    route = str(next(f['value'] for f in facts if f['field'] == 'production_route')).strip()
    if not route or year < 2026 or year > 2034:
        raise ValueError('INVALID_CBAM_PERIOD_OR_ROUTE')
    cn = next(iter(by_field['cn_code']))
    mass = weight / 1000
    allocation = free_allocation_adjustment(cn, float(mass), year, route)
    if not allocation.get('available'):
        raise ValueError('OFFICIAL_CBAM_BENCHMARK_OR_CSCF_REQUIRED')
    obligation = certificate_obligation(float(intensity), float(mass), allocation)
    return {'method': 'EU_CBAM_SHIPMENT_OBLIGATION_V2', 'reporting_year': year,
            'cn_code': cn, 'production_route': route, 'mass_t': str(mass),
            'specific_embedded_emissions_tco2e_per_t': str(intensity),
            'embedded_emissions_tco2e': str(mass * intensity),
            'free_allocation': allocation, 'certificate_obligation': obligation,
            'reference_snapshots': _reference_snapshots(),
            'input_fact_fields': ['cn_code', 'net_weight_kg', 'specific_embedded_emissions_tco2e_per_t',
                                  'production_route', 'reporting_year', 'verification_status'],
            'scope': 'versioned certificate estimate; registry acceptance and final surrender remain external'}


def _db():
    conn = _connect()
    conn.executescript(SCHEMA)
    return conn


def submit(dossier_id: str, tenant_id: str, actor: str, packet: dict) -> str:
    from .real_evidence import get
    state = get(dossier_id, tenant_id)
    calculation = validate_packet(state, packet)
    packet_id = str(uuid4())
    payload, digest, fingerprint = _canonical(packet), _hash(packet), evidence_fingerprint(state)
    with _db() as conn:
        conn.execute('BEGIN IMMEDIATE')
        _owned(conn, dossier_id, tenant_id)
        conn.execute('INSERT INTO real_release_packets(id,dossier_id,tenant_id,submitted_by,packet_json,packet_hash,evidence_hash,calculation_json,status,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)',
                     (packet_id, dossier_id, tenant_id, actor, payload, digest, fingerprint, _canonical(calculation), 'PENDING', _now()))
        _event(conn, dossier_id, actor, 'release.submitted', {'packet_id': packet_id, 'packet_hash': digest, 'evidence_hash': fingerprint})
        conn.commit()
    return packet_id


def decide(dossier_id: str, tenant_id: str, packet_id: str, actor: str, approve: bool, reason: str) -> None:
    from .real_evidence import get
    if not reason.strip():
        raise ValueError('REVIEW_REASON_REQUIRED')
    state = get(dossier_id, tenant_id)
    with _db() as conn:
        _owned(conn, dossier_id, tenant_id)
        row = conn.execute('SELECT * FROM real_release_packets WHERE id=? AND dossier_id=? AND tenant_id=?',
                           (packet_id, dossier_id, tenant_id)).fetchone()
        if row is None:
            raise KeyError('RELEASE_PACKET_NOT_FOUND')
        if row['status'] != 'PENDING':
            raise ValueError('RELEASE_ALREADY_DECIDED')
        if actor == row['submitted_by'] or actor in {d['uploaded_by'] for d in state['documents']}:
            raise ValueError('REVIEWER_MUST_BE_INDEPENDENT')
        packet = json.loads(row['packet_json'])
        if _hash(packet) != row['packet_hash'] or evidence_fingerprint(state) != row['evidence_hash']:
            raise ValueError('RELEASE_SOURCE_CHANGED')
        if approve:
            calculation = validate_packet(state, packet)
            if _canonical(calculation) != row['calculation_json']:
                raise ValueError('RELEASE_CALCULATION_CHANGED')
        decision = 'APPROVED' if approve else 'REJECTED'
        reviewed_at = _now()
        decision_hash = _hash({'packet_id': packet_id, 'packet_hash': row['packet_hash'],
                               'evidence_hash': row['evidence_hash'], 'calculation': json.loads(row['calculation_json']),
                               'decision': decision, 'reviewer': actor, 'reason': reason, 'reviewed_at': reviewed_at})
        conn.execute('BEGIN IMMEDIATE')
        updated = conn.execute('UPDATE real_release_packets SET status=?,reviewer=?,review_reason=?,decision_hash=?,reviewed_at=? WHERE id=? AND status=?',
                               (decision, actor, reason, decision_hash, reviewed_at, packet_id, 'PENDING'))
        if updated.rowcount != 1:
            raise ValueError('RELEASE_ALREADY_DECIDED')
        _event(conn, dossier_id, actor, 'release.decided', {'packet_id': packet_id, 'decision': decision,
                                                             'decision_hash': decision_hash, 'reason': reason})
        conn.commit()


def attach_status(state: dict) -> dict:
    dossier_id, tenant_id = state['dossier']['id'], state['dossier']['tenant_id']
    with _db() as conn:
        row = conn.execute('SELECT * FROM real_release_packets WHERE dossier_id=? AND tenant_id=? ORDER BY rowid DESC LIMIT 1',
                           (dossier_id, tenant_id)).fetchone()
    if row is None:
        return state
    row = dict(row)
    summary = {k: row[k] for k in ('id', 'status', 'submitted_by', 'reviewer', 'review_reason',
                                   'packet_hash', 'evidence_hash', 'decision_hash', 'created_at', 'reviewed_at')}
    summary['calculation'] = json.loads(row['calculation_json'])
    summary['packet'] = json.loads(row['packet_json'])
    state['release'] = summary
    if row['status'] != 'APPROVED':
        return state
    events = [e for e in state['events'] if e['kind'] == 'release.decided' and e['payload'].get('packet_id') == row['id']]
    expected = _hash({'packet_id': row['id'], 'packet_hash': row['packet_hash'],
                      'evidence_hash': row['evidence_hash'], 'calculation': summary['calculation'],
                      'decision': row['status'], 'reviewer': row['reviewer'], 'reason': row['review_reason'],
                      'reviewed_at': row['reviewed_at']})
    try:
        references_current = summary['calculation'].get('reference_snapshots') == _reference_snapshots()
    except ValueError:
        references_current = False
    sound = (references_current and _hash(json.loads(row['packet_json'])) == row['packet_hash']
             and row['decision_hash'] == expected and len(events) == 1
             and events[0]['payload'].get('decision_hash') == expected
             and events[0]['actor'] == row['reviewer']
             and evidence_fingerprint(state) == row['evidence_hash']
             and all(state['integrity'].values())
             and not state['graph']['conflicts']
             and all(e['status'] == 'APPROVED' for e in state['graph']['edges']))
    if sound and state['blockers'] == ['COMPLETE_EU_SHIPMENT_AND_VERIFIED_CBAM_NOT_ESTABLISHED']:
        state['decision'] = 'READY'
        state['blockers'] = []
    else:
        state['blockers'].append('RELEASE_INVALID_OR_STALE')
    return state
