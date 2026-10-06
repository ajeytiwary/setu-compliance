"""Tenant-scoped public/client document intake and review-gated candidate graph."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from . import db
from .public_document_ingest import extract_cbam_workbook, extract_public_pdf
from .pdf_observations import reconcile_documents

SCHEMA="""
CREATE TABLE IF NOT EXISTS real_dossiers (id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, name TEXT NOT NULL, created_by TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_real_dossiers_tenant ON real_dossiers(tenant_id);
CREATE TABLE IF NOT EXISTS real_documents (id TEXT PRIMARY KEY, dossier_id TEXT NOT NULL REFERENCES real_dossiers(id), filename TEXT NOT NULL, sha256 TEXT NOT NULL, blob BLOB NOT NULL, parsed_json TEXT NOT NULL, role TEXT NOT NULL, uploaded_by TEXT NOT NULL, reviewed_by TEXT, review_status TEXT NOT NULL, created_at TEXT NOT NULL, reviewed_at TEXT, UNIQUE(dossier_id,sha256));
CREATE INDEX IF NOT EXISTS idx_real_documents_dossier ON real_documents(dossier_id);
CREATE TABLE IF NOT EXISTS real_events (id INTEGER PRIMARY KEY AUTOINCREMENT, dossier_id TEXT NOT NULL REFERENCES real_dossiers(id), actor TEXT NOT NULL, kind TEXT NOT NULL, payload_json TEXT NOT NULL, previous_hash TEXT, event_hash TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_real_events_dossier ON real_events(dossier_id,id);
CREATE TABLE IF NOT EXISTS real_link_reviews (dossier_id TEXT NOT NULL REFERENCES real_dossiers(id), edge_id TEXT NOT NULL, status TEXT NOT NULL, reviewer TEXT NOT NULL, reason TEXT NOT NULL, reviewed_at TEXT NOT NULL, PRIMARY KEY(dossier_id,edge_id));
"""

def _now():return datetime.now(timezone.utc).isoformat()
def _connect():
    db.DB_PATH.parent.mkdir(parents=True,exist_ok=True)
    conn=sqlite3.connect(db.DB_PATH,timeout=15)
    conn.row_factory=sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    return conn

def _event(conn,dossier_id,actor,kind,payload):
    prev=conn.execute("SELECT event_hash FROM real_events WHERE dossier_id=? ORDER BY id DESC LIMIT 1",(dossier_id,)).fetchone()
    previous=prev[0] if prev else None;at=_now()
    canonical=json.dumps({"dossier_id":dossier_id,"actor":actor,"kind":kind,"payload":payload,"previous_hash":previous,"created_at":at},sort_keys=True,separators=(",",":"))
    digest=hashlib.sha256(canonical.encode()).hexdigest()
    conn.execute("INSERT INTO real_events(dossier_id,actor,kind,payload_json,previous_hash,event_hash,created_at) VALUES(?,?,?,?,?,?,?)",(dossier_id,actor,kind,json.dumps(payload,sort_keys=True),previous,digest,at))

def _owned(conn,dossier_id,tenant_id):
    row=conn.execute("SELECT * FROM real_dossiers WHERE id=? AND tenant_id=?",(dossier_id,tenant_id)).fetchone()
    if row is None:raise KeyError("DOSSIER_NOT_FOUND")
    return dict(row)

def _parse(data,filename):
    suffix=Path(filename).suffix.lower()
    if suffix==".pdf":
        if not data.startswith(b"%PDF-"):raise ValueError("INVALID_PDF")
        try:parsed=extract_public_pdf(data,filename)
        except Exception as exc:raise ValueError("PDF_PARSE_FAILED") from exc
        if parsed["observations"].get("code"):raise ValueError(parsed["observations"]["code"])
        return parsed
    if suffix==".xlsx":
        if not data.startswith(b"PK\x03\x04"):raise ValueError("INVALID_XLSX")
        try:parsed=extract_cbam_workbook(data,filename)
        except Exception as exc:raise ValueError("XLSX_PARSE_FAILED") from exc
        if parsed.get("code"):raise ValueError(parsed["code"])
        return parsed
    raise ValueError("UNSUPPORTED_FILE_TYPE")

def create(tenant_id,actor,name):
    dossier_id=str(uuid4())
    with _connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("INSERT INTO real_dossiers VALUES(?,?,?,?,?)",(dossier_id,tenant_id,name[:160],actor,_now()))
        _event(conn,dossier_id,actor,"dossier.created",{"name":name[:160]})
        conn.commit()
    return dossier_id

def add_document(dossier_id,tenant_id,actor,filename,data):
    if len(data)>8*1024*1024:raise ValueError("FILE_TOO_LARGE")
    parsed=_parse(data,filename)
    digest=hashlib.sha256(data).hexdigest();document_id=str(uuid4())
    with _connect() as conn:
        conn.execute("BEGIN IMMEDIATE");_owned(conn,dossier_id,tenant_id)
        existing=conn.execute("SELECT id FROM real_documents WHERE dossier_id=? AND sha256=?",(dossier_id,digest)).fetchone()
        if existing:return existing["id"]
        parsed_json=json.dumps(parsed,default=str,sort_keys=True)
        conn.execute("INSERT INTO real_documents(id,dossier_id,filename,sha256,blob,parsed_json,role,uploaded_by,review_status,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                     (document_id,dossier_id,Path(filename).name,digest,data,parsed_json,parsed["role"],actor,"PENDING",_now()))
        _event(conn,dossier_id,actor,"document.uploaded",{"document_id":document_id,"role":parsed["role"],"sha256":digest,"parsed_sha256":hashlib.sha256(parsed_json.encode()).hexdigest()})
        conn.commit()
    return document_id

def review_document(dossier_id,tenant_id,document_id,actor,approve,reason):
    if not reason.strip():raise ValueError("REVIEW_REASON_REQUIRED")
    with _connect() as conn:
        conn.execute("BEGIN IMMEDIATE");_owned(conn,dossier_id,tenant_id)
        row=conn.execute("SELECT * FROM real_documents WHERE id=? AND dossier_id=?",(document_id,dossier_id)).fetchone()
        if row is None:raise KeyError("DOCUMENT_NOT_FOUND")
        if row["uploaded_by"]==actor:raise ValueError("REVIEWER_MUST_DIFFER_FROM_SUBMITTER")
        data=bytes(row["blob"])
        if hashlib.sha256(data).hexdigest()!=row["sha256"]:raise ValueError("SOURCE_INTEGRITY_FAILED")
        actual=_parse(data,row["filename"]);stored=json.loads(row["parsed_json"])
        if _evidence(actual)!=_evidence(stored):raise ValueError("PARSED_SOURCE_MISMATCH")
        status="APPROVED" if approve else "REJECTED"
        conn.execute("UPDATE real_documents SET review_status=?,reviewed_by=?,reviewed_at=? WHERE id=?",(status,actor,_now(),document_id))
        _event(conn,dossier_id,actor,"document.reviewed",{"document_id":document_id,"status":status,"reason":reason})
        conn.commit()

def _evidence(parsed):
    if "observations" in parsed:
        obs=parsed["observations"]
        return {"fields":obs.get("fields"),"tables":obs.get("tables"),"sha256":obs.get("sha256")}
    return {"fields":parsed.get("fields"),"product_rows":parsed.get("product_rows"),"sha256":parsed.get("sha256")}

def get(dossier_id,tenant_id):
    with _connect() as conn:
        dossier=_owned(conn,dossier_id,tenant_id)
        rows=conn.execute("SELECT * FROM real_documents WHERE dossier_id=? ORDER BY created_at,id",(dossier_id,)).fetchall()
        events=[dict(r) for r in conn.execute("SELECT * FROM real_events WHERE dossier_id=? ORDER BY id",(dossier_id,)).fetchall()]
        link_reviews={r["edge_id"]:dict(r) for r in conn.execute("SELECT * FROM real_link_reviews WHERE dossier_id=?",(dossier_id,)).fetchall()}
    uploaded={json.loads(e["payload_json"])["document_id"]:json.loads(e["payload_json"]) for e in events if e["kind"]=="document.uploaded"}
    docs=[];source_ok=True
    for row in rows:
        item=dict(row);data=bytes(item.pop("blob"));parsed_json=item.pop("parsed_json");parsed=json.loads(parsed_json)
        item["parsed"]=parsed
        attested=uploaded.get(item["id"],{})
        item["integrity_ok"]=(hashlib.sha256(data).hexdigest()==item["sha256"]
            and attested.get("sha256")==item["sha256"]
            and attested.get("parsed_sha256")==hashlib.sha256(parsed_json.encode()).hexdigest())
        if not item["integrity_ok"]:source_ok=False
        docs.append(item)
    previous=None;audit_ok=True
    for event in events:
        payload=json.loads(event.pop("payload_json"));event["payload"]=payload
        canonical=json.dumps({"dossier_id":dossier_id,"actor":event["actor"],"kind":event["kind"],"payload":payload,"previous_hash":previous,"created_at":event["created_at"]},sort_keys=True,separators=(",",":"))
        if event["previous_hash"]!=previous or hashlib.sha256(canonical.encode()).hexdigest()!=event["event_hash"]:audit_ok=False
        previous=event["event_hash"]
    latest_doc_reviews={};latest_link_reviews={}
    for event in events:
        if event["kind"]=="document.reviewed":latest_doc_reviews[event["payload"]["document_id"]]=event
        if event["kind"]=="link.reviewed":latest_link_reviews[event["payload"]["edge_id"]]=event
    review_ok=True
    for doc in docs:
        event=latest_doc_reviews.get(doc["id"])
        if doc["review_status"]=="PENDING":
            if event:review_ok=False
        elif not event or event["payload"].get("status")!=doc["review_status"] or event["actor"]!=doc["reviewed_by"]:
            review_ok=False
    for edge_id,review in link_reviews.items():
        event=latest_link_reviews.get(edge_id)
        if not event or event["payload"].get("status")!=review["status"] or event["actor"]!=review["reviewer"]:
            review_ok=False
    recon_docs=[{"observations":d["parsed"].get("observations",{}) if d["integrity_ok"] else {}} for d in docs]
    graph=reconcile_documents(recon_docs)
    conflicts=[]
    for conflict in graph["conflicts"]:
        c=dict(conflict);c["document_ids"]=[docs[i]["id"] for i in c["documents"]]
        conflicts.append(c)
    edges=[]
    for edge in graph["edges"]:
        a,b=docs[edge["from"]],docs[edge["to"]]
        # Cross-document candidates cannot become trusted without independent review.
        edge_id=hashlib.sha256(json.dumps({"dossier_id":dossier_id,"documents":sorted((a["id"],b["id"])),"invoice_numbers":edge["invoice_numbers"],"container_numbers":edge["container_numbers"]},sort_keys=True).encode()).hexdigest()
        review=link_reviews.get(edge_id)
        edges.append({"id":edge_id,"from":a["id"],"to":b["id"],"invoice_numbers":edge["invoice_numbers"],
                      "container_numbers":edge["container_numbers"],"status":review["status"] if review else "CANDIDATE_REQUIRES_LINK_REVIEW",
                      "reviewed_by":review["reviewer"] if review else None,"review_reason":review["reason"] if review else None})
    blockers=[]
    if not source_ok:blockers.append("SOURCE_INTEGRITY_FAILED")
    if not audit_ok:blockers.append("AUDIT_INTEGRITY_FAILED")
    if not review_ok:blockers.append("REVIEW_AUDIT_MISMATCH")
    if graph["conflicts"]:blockers.append("SOURCE_VALUE_CONFLICT")
    if any(e["status"]!="APPROVED" for e in edges):blockers.append("LINK_REVIEW_REQUIRED")
    if any(d["review_status"]!="APPROVED" for d in docs):blockers.append("DOCUMENT_REVIEW_REQUIRED")
    # Real-world READY needs a complete linked chain and verified CBAM evidence.
    blockers.append("COMPLETE_EU_SHIPMENT_AND_VERIFIED_CBAM_NOT_ESTABLISHED")
    state={"dossier":dossier,"documents":docs,"graph":{"nodes":[{"id":d["id"],"role":d["role"],"sha256":d["sha256"],"review_status":d["review_status"]} for d in docs],"edges":edges,"conflicts":conflicts},"events":events,"integrity":{"sources":source_ok,"audit_chain":audit_ok,"reviews":review_ok},"decision":"BLOCKED","blockers":blockers}
    from .real_release import attach_status
    return attach_status(state)

def document_bytes(dossier_id,tenant_id,document_id):
    with _connect() as conn:
        _owned(conn,dossier_id,tenant_id)
        row=conn.execute("SELECT filename,sha256,blob FROM real_documents WHERE id=? AND dossier_id=?",(document_id,dossier_id)).fetchone()
        if row is None:raise KeyError("DOCUMENT_NOT_FOUND")
        data=bytes(row["blob"])
        if hashlib.sha256(data).hexdigest()!=row["sha256"]:raise ValueError("SOURCE_INTEGRITY_FAILED")
        return data,row["filename"]


def review_link(dossier_id,tenant_id,edge_id,actor,approve,reason):
    if not reason.strip():raise ValueError("REVIEW_REASON_REQUIRED")
    state=get(dossier_id,tenant_id)
    edge=next((e for e in state["graph"]["edges"] if e["id"]==edge_id),None)
    if edge is None:raise KeyError("LINK_NOT_FOUND")
    by_id={d["id"]:d for d in state["documents"]}
    a,b=by_id[edge["from"]],by_id[edge["to"]]
    if a["uploaded_by"]==actor or b["uploaded_by"]==actor:raise ValueError("REVIEWER_MUST_DIFFER_FROM_SUBMITTER")
    if a["review_status"]!="APPROVED" or b["review_status"]!="APPROVED":raise ValueError("SOURCE_REVIEW_REQUIRED")
    if not all(state["integrity"].values()):raise ValueError("INTEGRITY_FAILED")
    if approve and any(set(c["document_ids"])=={a["id"],b["id"]} for c in state["graph"]["conflicts"]):
        raise ValueError("UNRESOLVED_SOURCE_CONFLICT")
    status="APPROVED" if approve else "REJECTED"
    with _connect() as conn:
        conn.execute("BEGIN IMMEDIATE");_owned(conn,dossier_id,tenant_id)
        conn.execute("INSERT INTO real_link_reviews(dossier_id,edge_id,status,reviewer,reason,reviewed_at) VALUES(?,?,?,?,?,?) ON CONFLICT(dossier_id,edge_id) DO UPDATE SET status=excluded.status,reviewer=excluded.reviewer,reason=excluded.reason,reviewed_at=excluded.reviewed_at",(dossier_id,edge_id,status,actor,reason,_now()))
        _event(conn,dossier_id,actor,"link.reviewed",{"edge_id":edge_id,"documents":sorted((a["id"],b["id"])),"status":status,"reason":reason})
        conn.commit()
