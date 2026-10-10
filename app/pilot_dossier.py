"""Tenant-scoped, reviewer-audited synthetic dossier workflow.

Only the generated DEMO PDFs are supported by the one-click seed. Uploaded
customer evidence is never auto-approved. READY here is a demonstration state.
"""
from __future__ import annotations

import hashlib
import os
import json
import re
import sqlite3
import subprocess
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from . import db
from .cbam_engine import calculate_actual_steel
from .pdf_observations import _locate, _geometry

FIXTURES = Path(os.getenv("EUROSETU_DEMO_FIXTURES_PATH") or (Path(__file__).resolve().parents[1] / "data" / "demo_dossier"))
ROLES = ("INVOICE", "PACKING_LIST", "SHIPPING_BILL", "BILL_OF_LADING", "MTC", "SAD", "CBAM_INSTALLATION")
INITIAL = {"INVOICE":"invoice_initial.pdf","PACKING_LIST":"packing_initial.pdf",
           "SHIPPING_BILL":"shipping_initial.pdf","BILL_OF_LADING":"bl_initial.pdf",
           "MTC":"mtc_initial.pdf","SAD":"sad_initial.pdf","CBAM_INSTALLATION":"cbam_initial.pdf"}
CORRECTED = {"MTC": "mtc_corrected.pdf", "CBAM_INSTALLATION": "cbam_corrected.pdf"}
SCHEMA = """
CREATE TABLE IF NOT EXISTS pilot_dossiers (
 id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, reference TEXT NOT NULL,
 synthetic INTEGER NOT NULL CHECK(synthetic=1), created_by TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_pilot_dossiers_tenant ON pilot_dossiers(tenant_id,created_at);
CREATE TABLE IF NOT EXISTS pilot_dossier_documents (
 id TEXT PRIMARY KEY, dossier_id TEXT NOT NULL REFERENCES pilot_dossiers(id),
 role TEXT NOT NULL, version INTEGER NOT NULL, filename TEXT NOT NULL,
 sha256 TEXT NOT NULL, pdf BLOB NOT NULL, facts_json TEXT NOT NULL, rows_json TEXT NOT NULL,
 provenance_json TEXT NOT NULL, review_status TEXT NOT NULL DEFAULT 'PENDING', added_by TEXT NOT NULL,
 reviewed_by TEXT, reviewed_at TEXT, superseded_by TEXT, created_at TEXT NOT NULL,
 UNIQUE(dossier_id,role,version));
CREATE INDEX IF NOT EXISTS idx_pilot_docs_dossier ON pilot_dossier_documents(dossier_id,role,version);
CREATE TABLE IF NOT EXISTS pilot_dossier_events (
 id INTEGER PRIMARY KEY AUTOINCREMENT, dossier_id TEXT NOT NULL REFERENCES pilot_dossiers(id),
 actor TEXT NOT NULL, kind TEXT NOT NULL, payload_json TEXT NOT NULL,
 previous_hash TEXT, event_hash TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_pilot_events_dossier ON pilot_dossier_events(dossier_id,id);
"""


def _now(): return datetime.now(timezone.utc).isoformat()


def _connect():
    db.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn=sqlite3.connect(db.DB_PATH, timeout=15)
    conn.row_factory=sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    return conn


def _event(conn, dossier_id, actor, kind, payload):
    previous=conn.execute("SELECT event_hash FROM pilot_dossier_events WHERE dossier_id=? ORDER BY id DESC LIMIT 1",(dossier_id,)).fetchone()
    prev=previous[0] if previous else None
    stamp=_now()
    canonical=json.dumps({"dossier_id":dossier_id,"actor":actor,"kind":kind,"payload":payload,
                          "previous_hash":prev,"created_at":stamp},sort_keys=True,separators=(",",":"))
    digest=hashlib.sha256(canonical.encode()).hexdigest()
    conn.execute("INSERT INTO pilot_dossier_events(dossier_id,actor,kind,payload_json,previous_hash,event_hash,created_at) VALUES(?,?,?,?,?,?,?)",
                 (dossier_id,actor,kind,json.dumps(payload,sort_keys=True),prev,digest,stamp))


def _parse_pdf(data: bytes):
    if not data.startswith(b"%PDF-") or len(data)>2_000_000: raise ValueError("INVALID_DEMO_PDF")
    proc=subprocess.run(["pdftotext","-layout","-","-"],input=data,capture_output=True,timeout=10,check=False)
    if proc.returncode: raise ValueError("PDF_TEXT_FAILED")
    pages=proc.stdout.decode("utf-8","replace").split("\f")
    if "SYNTHETIC DEMONSTRATION DOCUMENT" not in pages[0]: raise ValueError("SYNTHETIC_LABEL_MISSING")
    geometry=_geometry(data)
    facts={}; rows=[]; provenance={}
    for p,text in enumerate(pages,1):
        words=geometry[p-1] if p<=len(geometry) else []
        for line_no,line in enumerate(text.splitlines(),1):
            raw=line.strip()
            if raw.startswith("ROW "):
                cells={}
                for part in raw.split("|")[1:]:
                    part=part.strip(); key,_,value=part.partition(" ")
                    if key and value: cells[key.lower()]=value.strip()
                rows.append({"cells":cells,"source":{"page":p,"line":line_no,"quote":raw,
                             "bbox":_locate(words,raw)}})
                continue
            if ": " not in raw: continue
            key,value=raw.split(": ",1)
            key=re.sub(r"[^a-z0-9]+","_",key.lower()).strip("_")
            if key in facts and facts[key]!=value: raise ValueError("DUPLICATE_FIELD_CONFLICT:"+key)
            facts[key]=value
            provenance[key]={"page":p,"line":line_no,"quote":raw,"bbox":_locate(words,value)}
    if facts.get("document_type") not in ROLES: raise ValueError("DOCUMENT_TYPE_INVALID")
    return facts,rows,provenance


def _insert_doc(conn,dossier_id,role,filename,data,actor):
    facts,rows,provenance=_parse_pdf(data)
    if facts["document_type"]!=role: raise ValueError("DOCUMENT_ROLE_MISMATCH")
    old=conn.execute("SELECT id,version FROM pilot_dossier_documents WHERE dossier_id=? AND role=? ORDER BY version DESC LIMIT 1",(dossier_id,role)).fetchone()
    version=(old["version"]+1) if old else 1
    doc_id=str(uuid4());digest=hashlib.sha256(data).hexdigest()
    conn.execute("INSERT INTO pilot_dossier_documents(id,dossier_id,role,version,filename,sha256,pdf,facts_json,rows_json,provenance_json,added_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                 (doc_id,dossier_id,role,version,filename,digest,data,json.dumps(facts),json.dumps(rows),json.dumps(provenance),actor,_now()))
    if old: conn.execute("UPDATE pilot_dossier_documents SET superseded_by=? WHERE id=?",(doc_id,old["id"]))
    _event(conn,dossier_id,actor,"document.added",{"document_id":doc_id,"role":role,"version":version,"sha256":digest,"supersedes":old["id"] if old else None})
    return doc_id


def _decision_payload(active):
    blockers,edges,calc=_assess(active)
    return {"status":"BLOCKED" if blockers else "READY", "blockers":blockers,
            "edges":edges,"active_documents":{role:doc["id"] for role,doc in active.items()},
            "calculation_input_hash":calc["input_hash"] if calc else None,
            "specific_embedded_emissions_tco2_per_t":calc["specific_embedded_emissions_tco2_per_t"] if calc else None,
            "shipment_embedded_emissions_tco2":calc["shipment_embedded_emissions_tco2"] if calc else None}


def _snapshot(conn,dossier_id,actor):
    docs=conn.execute("SELECT id,role,facts_json,rows_json,review_status FROM pilot_dossier_documents WHERE dossier_id=? AND superseded_by IS NULL",(dossier_id,)).fetchall()
    active={r["role"]:{"id":r["id"],"facts":json.loads(r["facts_json"]),"rows":json.loads(r["rows_json"]),"review_status":r["review_status"]} for r in docs}
    _event(conn,dossier_id,actor,"decision.evaluated",_decision_payload(active))


def create_demo(tenant_id:str,actor:str):
    dossier_id=str(uuid4())
    with _connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("INSERT INTO pilot_dossiers VALUES(?,?,?,?,?,?)",(dossier_id,tenant_id,"DEMO-EU-STEEL-2026-001",1,actor,_now()))
        _event(conn,dossier_id,actor,"dossier.created",{"synthetic":True})
        for role,filename in INITIAL.items():
            _insert_doc(conn,dossier_id,role,filename,(FIXTURES/filename).read_bytes(),actor)
        _snapshot(conn,dossier_id,actor)
        conn.commit()
    return dossier_id


def _owned(conn,dossier_id,tenant_id):
    row=conn.execute("SELECT * FROM pilot_dossiers WHERE id=? AND tenant_id=?",(dossier_id,tenant_id)).fetchone()
    if not row: raise KeyError("DOSSIER_NOT_FOUND")
    return dict(row)


def review_document(dossier_id,tenant_id,document_id,actor,approve:bool,reason:str):
    if not reason.strip(): raise ValueError("REVIEW_REASON_REQUIRED")
    with _connect() as conn:
        conn.execute("BEGIN IMMEDIATE");_owned(conn,dossier_id,tenant_id)
        doc=conn.execute("SELECT * FROM pilot_dossier_documents WHERE id=? AND dossier_id=?",(document_id,dossier_id)).fetchone()
        if not doc: raise KeyError("DOCUMENT_NOT_FOUND")
        if doc["superseded_by"]: raise ValueError("SUPERSEDED_DOCUMENT")
        if hashlib.sha256(bytes(doc["pdf"])).hexdigest()!=doc["sha256"]:
            raise ValueError("SOURCE_INTEGRITY_FAILED")
        parsed_facts,parsed_rows,parsed_provenance=_parse_pdf(bytes(doc["pdf"]))
        if (parsed_facts!=json.loads(doc["facts_json"]) or parsed_rows!=json.loads(doc["rows_json"])
                or parsed_provenance!=json.loads(doc["provenance_json"])):
            raise ValueError("PARSED_SOURCE_MISMATCH")
        if doc["added_by"] == actor: raise ValueError("REVIEWER_MUST_DIFFER_FROM_SUBMITTER")
        status="APPROVED" if approve else "REJECTED"
        conn.execute("UPDATE pilot_dossier_documents SET review_status=?,reviewed_by=?,reviewed_at=? WHERE id=?",
                     (status,actor,_now(),document_id))
        _event(conn,dossier_id,actor,"document.reviewed",{"document_id":document_id,"status":status,"reason":reason})
        _snapshot(conn,dossier_id,actor)
        conn.commit()
    return get_dossier(dossier_id,tenant_id)


def remediate(dossier_id,tenant_id,role,actor):
    if role not in CORRECTED: raise ValueError("NO_DEMO_REMEDIATION_FOR_ROLE")
    with _connect() as conn:
        conn.execute("BEGIN IMMEDIATE");_owned(conn,dossier_id,tenant_id)
        filename=CORRECTED[role]
        _insert_doc(conn,dossier_id,role,filename,(FIXTURES/filename).read_bytes(),actor)
        _snapshot(conn,dossier_id,actor)
        conn.commit()
    return get_dossier(dossier_id,tenant_id)


def _assess(active):
    blockers=[]; edges=[]
    def issue(code,detail,roles): blockers.append({"code":code,"detail":detail,"roles":roles})
    for role in ROLES:
        if role not in active: issue("DOCUMENT_MISSING",role,[role])
        elif active[role]["review_status"]!="APPROVED": issue("DOCUMENT_UNREVIEWED",role,[role])
    if len(active)!=len(ROLES): return blockers,edges,None
    facts={r:active[r]["facts"] for r in ROLES}
    required={"INVOICE":("invoice_date","invoice_value","currency","heat_number","coil_number"),
              "PACKING_LIST":("gross_weight_kg","packages","heat_number","coil_number"),
              "SHIPPING_BILL":("shipping_bill_number","shipping_date"),
              "BILL_OF_LADING":("bill_of_lading","on_board_date","port_of_discharge"),
              "MTC":("certificate_number","certificate_standard","heat_number","coil_number","manufacturer"),
              "SAD":("mrn","eori","declaration_date","bill_of_lading","customs_value_eur"),
              "CBAM_INSTALLATION":("installation_id","reporting_period","production_route","activity_level_t",
                                   "direct_emissions_tco2","precursor_quantity_t","precursor_see_tco2_t","monitoring_plan_ref")}
    for role,names in required.items():
        for name in names:
            if not facts[role].get(name): issue("REQUIRED_FIELD_MISSING",role+":"+name,[role])
    common=("invoice_number","purchase_order","origin_country","destination_country",
            "hs_cn_code","net_weight_kg","container_number")
    for role in ROLES:
        for name in common:
            if not facts[role].get(name): issue("REQUIRED_FIELD_MISSING",role+":"+name,[role])
    for role in ("INVOICE","PACKING_LIST","SAD"):
        if not active[role].get("rows"):
            issue("ITEM_ROWS_MISSING",role,[role])
    for role,names in {"INVOICE":("invoice_value","net_weight_kg"),
                       "PACKING_LIST":("gross_weight_kg","net_weight_kg","packages"),
                       "SAD":("customs_value_eur","net_weight_kg")}.items():
        for name in names:
            value=facts[role].get(name)
            if value:
                try:
                    if Decimal(value)<=0: raise InvalidOperation
                except InvalidOperation:
                    issue("INVALID_POSITIVE_NUMBER",role+":"+name,[role])
    for role,doc in active.items():
        for row in doc.get("rows",[]):
            for cell_key,fact_key in (("cn","hs_cn_code"),("heat","heat_number"),("coil","coil_number"),
                                      ("kg","net_weight_kg"),("eur","invoice_value"),("packages","packages")):
                observed=row["cells"].get(cell_key); header=doc["facts"].get(fact_key)
                if not observed or not header: continue
                try:
                    equal=Decimal(observed)==Decimal(header) if cell_key in {"kg","eur","packages"} else observed==header
                except InvalidOperation: equal=False
                if not equal: issue("ROW_FIELD_CONFLICT",role+":"+cell_key,[role])
    invoice=facts["INVOICE"]
    comparable=("invoice_number","purchase_order","origin_country","destination_country",
                "hs_cn_code","net_weight_kg","container_number")
    for role in ROLES:
        if role=="INVOICE":continue
        shared=[]
        for key in comparable:
            a,b=invoice.get(key),facts[role].get(key)
            if a and b:
                if a!=b: issue("FIELD_CONFLICT",f"{key}: {a} != {b}",["INVOICE",role])
                else: shared.append(key)
        if "invoice_number" not in shared or "container_number" not in shared:
            issue("LINK_ANCHOR_MISSING",role,["INVOICE",role])
        else: edges.append({"from":active["INVOICE"]["id"],"to":active[role]["id"],"anchors":shared})
    if facts["MTC"].get("heat_number")!=invoice.get("heat_number"):
        issue("HEAT_MISMATCH","MTC heat differs from invoice",["MTC","INVOICE"])
    if facts["MTC"].get("coil_number")!=invoice.get("coil_number"):
        issue("COIL_MISMATCH","MTC coil differs from invoice",["MTC","INVOICE"])
    if facts["SAD"].get("bill_of_lading")!=facts["BILL_OF_LADING"].get("bill_of_lading"):
        issue("BL_MISMATCH","SAD B/L differs from transport B/L",["SAD","BILL_OF_LADING"])
    if facts["INVOICE"].get("currency")=="EUR" and facts["SAD"].get("customs_value_eur")!=facts["INVOICE"].get("invoice_value"):
        issue("CUSTOMS_VALUE_MISMATCH","SAD customs value differs from EUR invoice value",["SAD","INVOICE"])
    if facts["CBAM_INSTALLATION"].get("verifier_status")!="VERIFIED" or not facts["CBAM_INSTALLATION"].get("verifier_report_ref"):
        issue("CBAM_VERIFICATION_MISSING","Actual emissions lack a verified report",["CBAM_INSTALLATION"])
    calc=None
    try:
        cbam=facts["CBAM_INSTALLATION"]
        payload={"cn_code":invoice["hs_cn_code"],"reporting_period":int(cbam["reporting_period"]),
                 "production_date":"2026-09-15","installation_id":cbam["installation_id"],
                 "production_route":cbam["production_route"],"production_process":"steel_making",
                 "activity_level_t":float(cbam["activity_level_t"]),
                 "monitoring_plan_ref":cbam["monitoring_plan_ref"],
                 "direct_emission_sources":[{"source_id":"DEMO-FURNACE","measured_emissions_tco2":float(cbam["direct_emissions_tco2"])}],
                 "precursors":[{"material":"demo ferroalloy","quantity_t":float(cbam["precursor_quantity_t"]),
                                "specific_embedded_emissions_tco2_per_t":float(cbam["precursor_see_tco2_t"]),"value_type":"ACTUAL"}],
                 "verification":{"status":cbam.get("verifier_status","UNVERIFIED")}}
        calc=calculate_actual_steel(payload)
        calc["shipment_embedded_emissions_tco2"]=round(float(invoice["net_weight_kg"])/1000*calc["specific_embedded_emissions_tco2_per_t"],9)
        calc["synthetic_demonstration"]=True
    except (KeyError,ValueError,TypeError) as exc:
        issue("CBAM_CALCULATION_FAILED",type(exc).__name__,["CBAM_INSTALLATION","INVOICE"])
    return blockers,edges,calc


def get_dossier(dossier_id,tenant_id):
    with _connect() as conn:
        dossier=_owned(conn,dossier_id,tenant_id)
        raw=conn.execute("SELECT id,role,version,filename,sha256,pdf,facts_json,rows_json,provenance_json,review_status,added_by,reviewed_by,reviewed_at,superseded_by,created_at FROM pilot_dossier_documents WHERE dossier_id=? ORDER BY role,version",(dossier_id,)).fetchall()
        docs=[]
        source_integrity=True
        for row in raw:
            item=dict(row)
            pdf_bytes=bytes(item.pop("pdf"))
            source_integrity &= hashlib.sha256(pdf_bytes).hexdigest()==item["sha256"]
            try:
                parsed_facts,parsed_rows,parsed_provenance=_parse_pdf(pdf_bytes)
                source_integrity &= (parsed_facts==json.loads(item["facts_json"]) and parsed_rows==json.loads(item["rows_json"])
                                     and parsed_provenance==json.loads(item["provenance_json"]))
            except (ValueError,subprocess.TimeoutExpired): source_integrity=False
            for key in ("facts_json","rows_json","provenance_json"):
                item[key.removesuffix("_json")]=json.loads(item.pop(key))
            docs.append(item)
        events=[{**dict(r),"payload":json.loads(r["payload_json"])} for r in conn.execute("SELECT * FROM pilot_dossier_events WHERE dossier_id=? ORDER BY id",(dossier_id,)).fetchall()]
        for event in events:event.pop("payload_json")
    audit_integrity=True; previous=None
    for event in events:
        canonical=json.dumps({"dossier_id":dossier_id,"actor":event["actor"],"kind":event["kind"],
                              "payload":event["payload"],"previous_hash":previous,"created_at":event["created_at"]},
                             sort_keys=True,separators=(",",":"))
        if event["previous_hash"]!=previous or hashlib.sha256(canonical.encode()).hexdigest()!=event["event_hash"]:
            audit_integrity=False
        previous=event["event_hash"]
    active={d["role"]:d for d in docs if not d["superseded_by"]}
    blockers,edges,calc=_assess(active)
    latest=next((e["payload"] for e in reversed(events) if e["kind"]=="decision.evaluated"),None)
    decision_integrity=latest==_decision_payload(active)
    if not decision_integrity: blockers.append({"code":"DECISION_SNAPSHOT_MISMATCH","detail":"Persisted graph or decision differs from active sources","roles":[]})
    if not source_integrity: blockers.append({"code":"SOURCE_INTEGRITY_FAILED","detail":"Stored PDF digest mismatch","roles":[]})
    if not audit_integrity: blockers.append({"code":"AUDIT_INTEGRITY_FAILED","detail":"Audit hash chain mismatch","roles":[]})
    return {"dossier":dossier,"documents":docs,"active_document_ids":{k:v["id"] for k,v in active.items()},
            "evidence_graph":{"nodes":[{"id":d["id"],"role":d["role"],"sha256":d["sha256"],"status":d["review_status"],"active":not bool(d["superseded_by"])} for d in docs],"edges":edges},
            "calculation":calc,"decision":"BLOCKED" if blockers else "READY",
            "blockers":blockers,"events":events,"integrity":{"source_pdfs":source_integrity,"audit_chain":audit_integrity,"decision_snapshot":decision_integrity},"synthetic_demonstration":True}


def document_pdf(dossier_id,tenant_id,document_id):
    with _connect() as conn:
        _owned(conn,dossier_id,tenant_id)
        row=conn.execute("SELECT pdf,filename,sha256 FROM pilot_dossier_documents WHERE id=? AND dossier_id=?",(document_id,dossier_id)).fetchone()
        if not row: raise KeyError("DOCUMENT_NOT_FOUND")
        data=bytes(row["pdf"])
        if hashlib.sha256(data).hexdigest()!=row["sha256"]: raise ValueError("SOURCE_INTEGRITY_FAILED")
        return data,row["filename"]
