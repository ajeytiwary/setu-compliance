from __future__ import annotations
import json, sqlite3
from contextlib import contextmanager
from pathlib import Path
DB_PATH=Path(__file__).resolve().parents[1]/"data"/"eurosetu.db"
SCHEMA="""PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS shipments(id TEXT PRIMARY KEY,shipment_no TEXT UNIQUE NOT NULL,exporter TEXT NOT NULL,facility TEXT NOT NULL,importer TEXT NOT NULL,destination_country TEXT NOT NULL,product TEXT NOT NULL,cn_code TEXT NOT NULL,tonnes REAL NOT NULL,value_eur REAL NOT NULL,emissions_method TEXT NOT NULL DEFAULT 'actual',embedded_emissions_tco2e_per_t REAL,supplier_required INTEGER NOT NULL DEFAULT 0,supplier_complete INTEGER NOT NULL DEFAULT 0,manual_hours REAL NOT NULL DEFAULT 0,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS requirements(id INTEGER PRIMARY KEY AUTOINCREMENT,shipment_id TEXT NOT NULL,code TEXT NOT NULL,label TEXT NOT NULL,category TEXT NOT NULL,blocking INTEGER NOT NULL DEFAULT 1,status TEXT NOT NULL DEFAULT 'MISSING',required_evidence INTEGER NOT NULL DEFAULT 0,evidence_count INTEGER NOT NULL DEFAULT 0,notes TEXT,UNIQUE(shipment_id,code),FOREIGN KEY(shipment_id) REFERENCES shipments(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS evidence(id TEXT PRIMARY KEY,shipment_id TEXT NOT NULL,requirement_code TEXT NOT NULL,filename TEXT NOT NULL,evidence_type TEXT NOT NULL,issuer TEXT,sha256 TEXT NOT NULL,valid_until TEXT,created_at TEXT NOT NULL,FOREIGN KEY(shipment_id) REFERENCES shipments(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS verifications(id TEXT PRIMARY KEY,shipment_id TEXT NOT NULL,verifier TEXT NOT NULL,status TEXT NOT NULL,started_at TEXT NOT NULL,completed_at TEXT,finding_count INTEGER NOT NULL DEFAULT 0,report_ref TEXT,FOREIGN KEY(shipment_id) REFERENCES shipments(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS public_sources(id INTEGER PRIMARY KEY AUTOINCREMENT,shipment_id TEXT NOT NULL,title TEXT NOT NULL,url TEXT NOT NULL,published TEXT,claim TEXT NOT NULL,FOREIGN KEY(shipment_id) REFERENCES shipments(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS app_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS integration_runs(id TEXT PRIMARY KEY,connector TEXT NOT NULL,source_name TEXT NOT NULL,status TEXT NOT NULL,rows_received INTEGER NOT NULL DEFAULT 0,rows_accepted INTEGER NOT NULL DEFAULT 0,rows_rejected INTEGER NOT NULL DEFAULT 0,started_at TEXT NOT NULL,completed_at TEXT,error_json TEXT);
CREATE TABLE IF NOT EXISTS canonical_records(id TEXT PRIMARY KEY,run_id TEXT NOT NULL,connector TEXT NOT NULL,record_type TEXT NOT NULL,source_key TEXT NOT NULL,payload_json TEXT NOT NULL,sha256 TEXT NOT NULL,created_at TEXT NOT NULL,FOREIGN KEY(run_id) REFERENCES integration_runs(id) ON DELETE CASCADE);
CREATE INDEX IF NOT EXISTS idx_canonical_type ON canonical_records(record_type); CREATE INDEX IF NOT EXISTS idx_canonical_source ON canonical_records(connector,source_key);
CREATE TABLE IF NOT EXISTS genealogy_edges(id TEXT PRIMARY KEY,run_id TEXT NOT NULL,event_time TEXT,facility TEXT,process TEXT,parent_type TEXT,parent_id TEXT,child_type TEXT,child_id TEXT,quantity_t REAL,production_line TEXT,FOREIGN KEY(run_id) REFERENCES integration_runs(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS activity_records(id TEXT PRIMARY KEY,run_id TEXT NOT NULL,event_time TEXT,facility TEXT,source_id TEXT,activity_type TEXT,quantity REAL,unit TEXT,measurement_method TEXT,quality TEXT,payload_json TEXT NOT NULL,FOREIGN KEY(run_id) REFERENCES integration_runs(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS trade_documents(id TEXT PRIMARY KEY,run_id TEXT NOT NULL,shipment_ref TEXT,document_type TEXT NOT NULL,document_ref TEXT,status TEXT,payload_json TEXT NOT NULL,created_at TEXT NOT NULL,FOREIGN KEY(run_id) REFERENCES integration_runs(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS supplier_evidence_records(id TEXT PRIMARY KEY,run_id TEXT NOT NULL,supplier_id TEXT,installation_id TEXT,evidence_type TEXT,status TEXT,payload_json TEXT NOT NULL,created_at TEXT NOT NULL,FOREIGN KEY(run_id) REFERENCES integration_runs(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS cbam_calculations(id TEXT PRIMARY KEY,methodology_id TEXT NOT NULL,installation_id TEXT,reporting_period TEXT,cn_code TEXT NOT NULL,production_route TEXT,activity_level_t REAL NOT NULL,specific_embedded_emissions REAL NOT NULL,payload_json TEXT NOT NULL,result_json TEXT NOT NULL,input_hash TEXT NOT NULL,status TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_cbam_calc_period ON cbam_calculations(reporting_period,cn_code);
CREATE TABLE IF NOT EXISTS origin_evaluations(id TEXT PRIMARY KEY,agreement_id TEXT NOT NULL,shipment_ref TEXT,shipment_date TEXT NOT NULL,hs_code TEXT NOT NULL,legal_regime TEXT NOT NULL,preference_available INTEGER NOT NULL DEFAULT 0,tariff_saving_eur REAL NOT NULL DEFAULT 0,payload_json TEXT NOT NULL,result_json TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS suppliers(id TEXT PRIMARY KEY,name TEXT NOT NULL,facility TEXT,country TEXT NOT NULL DEFAULT 'IN',status TEXT NOT NULL DEFAULT 'ACTIVE',created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS supplier_evidence(id TEXT PRIMARY KEY,supplier_id TEXT NOT NULL,evidence_type TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'PENDING',issuer TEXT,verifier TEXT,valid_from TEXT,valid_until TEXT,sha256 TEXT,source_ref TEXT,metadata_json TEXT NOT NULL DEFAULT '{}',created_at TEXT NOT NULL,updated_at TEXT NOT NULL,FOREIGN KEY(supplier_id) REFERENCES suppliers(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS supplier_shipment_links(id TEXT PRIMARY KEY,supplier_id TEXT NOT NULL,shipment_id TEXT NOT NULL,material TEXT,quantity_t REAL,required_evidence_type TEXT,created_at TEXT NOT NULL,UNIQUE(supplier_id,shipment_id,material),FOREIGN KEY(supplier_id) REFERENCES suppliers(id) ON DELETE CASCADE,FOREIGN KEY(shipment_id) REFERENCES shipments(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS evidence_requests(id TEXT PRIMARY KEY,shipment_id TEXT NOT NULL,supplier_id TEXT NOT NULL,requirement_code TEXT NOT NULL,evidence_type TEXT NOT NULL,owner TEXT NOT NULL,due_date TEXT,status TEXT NOT NULL DEFAULT 'OPEN',message TEXT,submitted_evidence_id TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,resolved_at TEXT,FOREIGN KEY(shipment_id) REFERENCES shipments(id) ON DELETE CASCADE,FOREIGN KEY(supplier_id) REFERENCES suppliers(id) ON DELETE CASCADE,FOREIGN KEY(submitted_evidence_id) REFERENCES supplier_evidence(id));
CREATE INDEX IF NOT EXISTS idx_supplier_evidence_supplier ON supplier_evidence(supplier_id,status);
CREATE INDEX IF NOT EXISTS idx_evidence_requests_shipment ON evidence_requests(shipment_id,status);
CREATE TABLE IF NOT EXISTS audit_events(id INTEGER PRIMARY KEY AUTOINCREMENT,shipment_id TEXT,event_type TEXT NOT NULL,payload TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS leads(id TEXT PRIMARY KEY,name TEXT NOT NULL,work_email TEXT UNIQUE NOT NULL,company TEXT NOT NULL,role TEXT,message TEXT,token TEXT UNIQUE NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS regulatory_change_impacts(id TEXT PRIMARY KEY,dataset TEXT NOT NULL,old_sha TEXT,new_sha TEXT NOT NULL,shipment_id TEXT NOT NULL,shipment_no TEXT NOT NULL,rule_codes TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'REVIEW_REQUIRED',created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_reg_change_status ON regulatory_change_impacts(status,created_at);
"""
@contextmanager
def connect():
 DB_PATH.parent.mkdir(parents=True,exist_ok=True); conn=sqlite3.connect(DB_PATH); conn.row_factory=sqlite3.Row; conn.execute("PRAGMA foreign_keys=ON")
 try: yield conn; conn.commit()
 finally: conn.close()
def init_db():
 with connect() as conn: conn.executescript(SCHEMA)
def rows(conn,query,params=()): return [dict(r) for r in conn.execute(query,params).fetchall()]
def row(conn,query,params=()):
 r=conn.execute(query,params).fetchone(); return dict(r) if r else None
def audit(conn,shipment_id,event_type,payload):
 from datetime import datetime,timezone
 conn.execute("INSERT INTO audit_events(shipment_id,event_type,payload,created_at) VALUES(?,?,?,?)",(shipment_id,event_type,json.dumps(payload,separators=(',',':')),datetime.now(timezone.utc).isoformat()))
