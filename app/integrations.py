from __future__ import annotations
import csv,hashlib,io,json,os
from dataclasses import dataclass
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from uuid import uuid4
from .db import connect,rows,audit
ROOT=Path(__file__).resolve().parents[1]; SAMPLE_DIR=ROOT/"connectors"/"samples"
@dataclass(frozen=True)
class ConnectorSpec:
 code:str; label:str; sample:str; required:tuple[str,...]; canonical_type:str; mode:str="CSV/API"; env_url:str|None=None
CONNECTORS={
"sap_sd":ConnectorSpec("sap_sd","SAP SD/FI","sap_sd.csv",("shipment_id","sales_order","delivery_id","invoice_id","destination_country","material_id","quantity_t","invoice_value_eur","currency","cn_code"),"shipment",env_url="SETU_SAP_SD_URL"),
"sap_mm":ConnectorSpec("sap_mm","SAP MM/PP","sap_mm.csv",("material_document","posting_date","material_id","batch_id","supplier_id","quantity","unit","plant","country_of_origin"),"material_movement",env_url="SETU_SAP_MM_URL"),
"oracle_erp":ConnectorSpec("oracle_erp","Oracle ERP","oracle_erp.csv",("shipment_id","order_no","invoice_no","customer","destination","value_eur","material"),"shipment_finance",env_url="SETU_ORACLE_ERP_URL"),
"tally":ConnectorSpec("tally","Tally","tally_export.csv",("shipment_id","ledger","invoice_no","party","value","currency"),"shipment_finance"),
"mes":ConnectorSpec("mes","MES genealogy","mes_genealogy.csv",("event_time","plant","process","parent_type","parent_id","child_type","child_id","quantity_t","production_line"),"genealogy",env_url="SETU_MES_URL"),
"scada_ems":ConnectorSpec("scada_ems","SCADA / EMS","scada_ems.csv",("facility","meter_id","activity","timestamp","quantity","unit","quality"),"activity",env_url="SETU_SCADA_URL"),
"ems_activity":ConnectorSpec("ems_activity","Environmental activity ledger","ems_activity.csv",("timestamp","installation","production_process","source_id","activity_type","quantity","unit","measurement_method","quality_flag"),"activity",env_url="SETU_EMS_URL"),
"lims":ConnectorSpec("lims","LIMS","lims.csv",("coil_id","test_id","standard","chemistry_status","mechanical_status","certificate_ref"),"quality",env_url="SETU_LIMS_URL"),
"gst":ConnectorSpec("gst","GST invoice","gst_invoice.csv",("shipment_id","gstin","invoice_no","invoice_date","taxable_value","currency"),"trade_document"),
"dgft_coo":ConnectorSpec("dgft_coo","DGFT / Certificate of Origin","dgft_coo.csv",("shipment_id","iec","agreement","origin_rule","qualification_status","coo_number","issue_date"),"trade_document"),
"icegate":ConnectorSpec("icegate","ICEGATE shipping bill","icegate_shipping_bill.csv",("shipment_id","shipping_bill_no","shipping_bill_date","port","hs_code","invoice_value","currency","destination"),"trade_document"),
"supplier_cbam":ConnectorSpec("supplier_cbam","Supplier CBAM","supplier_cbam.csv",("supplier_id","installation_id","precursor_cn","precursor_name","period_start","period_end","specific_embedded_emissions","unit","verification_status","evidence_ref"),"supplier_evidence"),
"verifier":ConnectorSpec("verifier","Verifier / Lab","verifier.csv",("installation_id","reporting_period","verifier","accreditation_ref","status","started_at","findings","statement_ref"),"verification",env_url="SETU_VERIFIER_URL"),
"logistics":ConnectorSpec("logistics","Logistics / Bill of Lading","logistics.csv",("shipment_id","container_no","bill_of_lading","port_of_loading","port_of_discharge","departure_date","status"),"trade_document",env_url="SETU_LOGISTICS_URL")}
def _now():return datetime.now(timezone.utc).isoformat()
def _float(v):
 if v in (None,""):return None
 try:return float(v)
 except (TypeError,ValueError):return None
def parse_csv(spec,csv_content):
 reader=csv.DictReader(io.StringIO(csv_content))
 if not reader.fieldnames:raise ValueError("CSV has no header")
 missing=[x for x in spec.required if x not in reader.fieldnames]
 if missing:raise ValueError("Missing required columns: "+", ".join(missing))
 return [{k:(v.strip() if isinstance(v,str) else v) for k,v in r.items()} for r in reader if any((v or "").strip() for v in r.values())]
def validate_records(spec,records):
 good=[]; errors=[]
 for i,rec in enumerate(records,start=2):
  missing=[k for k in spec.required if rec.get(k) in (None,"")]
  (errors if missing else good).append({"row":i,"error":"missing_required_values","fields":missing,"record":rec} if missing else rec)
 return good,errors
def normalize(spec,rec):
 c=spec.code
 if c=="sap_sd":return {"shipment_id":rec["shipment_id"],"order_no":rec["sales_order"],"delivery_id":rec["delivery_id"],"invoice_no":rec["invoice_id"],"customer":rec.get("customer_id"),"destination":rec["destination_country"],"material_id":rec["material_id"],"batch_id":rec.get("batch_id"),"quantity_t":_float(rec["quantity_t"]),"value_eur":_float(rec["invoice_value_eur"]),"currency":rec["currency"],"cn_code":rec["cn_code"]}
 if c=="sap_mm":return {"document_no":rec["material_document"],"posting_date":rec["posting_date"],"material_id":rec["material_id"],"batch_id":rec["batch_id"],"supplier_id":rec["supplier_id"],"quantity":_float(rec["quantity"]),"unit":rec["unit"],"facility":rec["plant"],"purchase_order":rec.get("purchase_order"),"country_of_origin":rec["country_of_origin"]}
 if c=="mes":return {"event_time":rec["event_time"],"facility":rec["plant"],"process":rec["process"],"parent_type":rec["parent_type"],"parent_id":rec["parent_id"],"child_type":rec["child_type"],"child_id":rec["child_id"],"quantity_t":_float(rec["quantity_t"]),"production_line":rec["production_line"]}
 if c in ("scada_ems","ems_activity"):
  if c=="scada_ems":return {"timestamp":rec["timestamp"],"facility":rec["facility"],"source_id":rec["meter_id"],"activity_type":rec["activity"],"quantity":_float(rec["quantity"]),"unit":rec["unit"],"measurement_method":"SCADA","quality":rec["quality"]}
  return {"timestamp":rec["timestamp"],"facility":rec["installation"],"process":rec["production_process"],"source_id":rec["source_id"],"activity_type":rec["activity_type"],"quantity":_float(rec["quantity"]),"unit":rec["unit"],"measurement_method":rec["measurement_method"],"quality":rec["quality_flag"],"measured_emissions_tco2":_float(rec.get("measured_emissions_tco2")),"emission_factor_tco2_per_unit":_float(rec.get("emission_factor_tco2_per_unit")),"oxidation_factor":_float(rec.get("oxidation_factor")),"conversion_factor":_float(rec.get("conversion_factor"))}
 if c=="supplier_cbam":return {**rec,"specific_embedded_emissions":_float(rec["specific_embedded_emissions"])}
 if c=="verifier":return {**rec,"findings":int(float(rec.get("findings") or 0))}
 return dict(rec)
def _key(rec,idx):
 for k in ("shipment_id","material_document","event_time","coil_id","supplier_id","installation_id","invoice_no","shipping_bill_no"):
  if rec.get(k):return str(rec[k])
 return f"row-{idx}"
def _persist(conn,run_id,spec,norm,raw,idx):
 rid=str(uuid4()); payload=json.dumps(norm,separators=(",",":")); digest=hashlib.sha256(payload.encode()).hexdigest()
 conn.execute("INSERT INTO canonical_records(id,run_id,connector,record_type,source_key,payload_json,sha256,created_at) VALUES(?,?,?,?,?,?,?,?)",(rid,run_id,spec.code,spec.canonical_type,_key(raw,idx),payload,digest,_now()))
 if spec.canonical_type=="genealogy":conn.execute("INSERT INTO genealogy_edges(id,run_id,event_time,facility,process,parent_type,parent_id,child_type,child_id,quantity_t,production_line) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(str(uuid4()),run_id,norm.get("event_time"),norm.get("facility"),norm.get("process"),norm.get("parent_type"),norm.get("parent_id"),norm.get("child_type"),norm.get("child_id"),norm.get("quantity_t"),norm.get("production_line")))
 elif spec.canonical_type=="activity":conn.execute("INSERT INTO activity_records(id,run_id,event_time,facility,source_id,activity_type,quantity,unit,measurement_method,quality,payload_json) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(str(uuid4()),run_id,norm.get("timestamp"),norm.get("facility"),norm.get("source_id"),norm.get("activity_type"),norm.get("quantity"),norm.get("unit"),norm.get("measurement_method"),norm.get("quality"),payload))
 elif spec.canonical_type=="trade_document":conn.execute("INSERT INTO trade_documents(id,run_id,shipment_ref,document_type,document_ref,status,payload_json,created_at) VALUES(?,?,?,?,?,?,?,?)",(str(uuid4()),run_id,norm.get("shipment_id"),spec.code,norm.get("coo_number") or norm.get("shipping_bill_no") or norm.get("invoice_no") or norm.get("bill_of_lading"),norm.get("qualification_status") or "INGESTED",payload,_now()))
 elif spec.canonical_type=="supplier_evidence":conn.execute("INSERT INTO supplier_evidence_records(id,run_id,supplier_id,installation_id,evidence_type,status,payload_json,created_at) VALUES(?,?,?,?,?,?,?,?)",(str(uuid4()),run_id,norm.get("supplier_id"),norm.get("installation_id"),"CBAM_PRECURSOR",norm.get("verification_status"),payload,_now()))
def import_csv(connector,csv_content,source_name="api"):
 spec=CONNECTORS[connector]; parsed=parse_csv(spec,csv_content); good,errors=validate_records(spec,parsed); run_id=str(uuid4())
 with connect() as conn:
  conn.execute("INSERT INTO integration_runs(id,connector,source_name,status,rows_received,rows_accepted,rows_rejected,started_at,completed_at,error_json) VALUES(?,?,?,?,?,?,?,?,?,?)",(run_id,connector,source_name,"RUNNING",len(parsed),0,0,_now(),None,None))
  for idx,rec in enumerate(good,start=1):_persist(conn,run_id,spec,normalize(spec,rec),rec,idx)
  status="SUCCESS" if not errors else ("PARTIAL" if good else "FAILED"); conn.execute("UPDATE integration_runs SET status=?,rows_accepted=?,rows_rejected=?,completed_at=?,error_json=? WHERE id=?",(status,len(good),len(errors),_now(),json.dumps(errors),run_id)); audit(conn,None,"integration.imported",{"run_id":run_id,"connector":connector,"accepted":len(good),"rejected":len(errors)})
 return {"run_id":run_id,"connector":connector,"status":status,"rows_received":len(parsed),"rows_accepted":len(good),"rows_rejected":len(errors),"errors":errors}
def import_sample(connector):
 spec=CONNECTORS[connector]; return import_csv(connector,(SAMPLE_DIR/spec.sample).read_text(),f"sample:{spec.sample}")
def integration_catalog():
 with connect() as conn:
  last={r["connector"]:r for r in rows(conn,"SELECT r.* FROM integration_runs r JOIN (SELECT connector,MAX(started_at) m FROM integration_runs GROUP BY connector)x ON r.connector=x.connector AND r.started_at=x.m")}
 return {"connectors":[{"code":c,"label":s.label,"canonical_type":s.canonical_type,"mode":s.mode,"sample":s.sample,"required_columns":list(s.required),"live_api_configured":bool(os.getenv(s.env_url)) if s.env_url else False,"live_api_url_env":s.env_url,"last_run":last.get(c)} for c,s in CONNECTORS.items()],"note":"CSV ingestion is executable. Live API polling requires customer endpoints/credentials."}
def canonical_summary():
 with connect() as conn:return {"records_by_type":rows(conn,"SELECT record_type,COUNT(*) count FROM canonical_records GROUP BY record_type ORDER BY record_type"),"genealogy_edges":conn.execute("SELECT COUNT(*) FROM genealogy_edges").fetchone()[0],"activity_records":conn.execute("SELECT COUNT(*) FROM activity_records").fetchone()[0],"trade_documents":conn.execute("SELECT COUNT(*) FROM trade_documents").fetchone()[0],"supplier_evidence":conn.execute("SELECT COUNT(*) FROM supplier_evidence_records").fetchone()[0],"recent_runs":rows(conn,"SELECT * FROM integration_runs ORDER BY started_at DESC LIMIT 20")}
