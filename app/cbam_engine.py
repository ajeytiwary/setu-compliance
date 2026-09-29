from __future__ import annotations
"""Versioned CBAM calculation engine for the definitive period."""
from datetime import date,datetime,timezone
from typing import Any
from uuid import uuid4
import hashlib,json
from .db import connect,rows,audit

METHODOLOGIES={"EU_CBAM_2026_2547":{"id":"EU_CBAM_2026_2547","title":"CBAM definitive-period embedded-emissions methodology","legal_basis":["Regulation (EU) 2023/956, Annex IV","Commission Implementing Regulation (EU) 2025/2547"],"effective_from":"2026-01-01","effective_to":None,"source":"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32025R2547","guidance":"https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism/cbam-legislation-and-guidance_en","steel_indirect_in_scope":False,"notes":"Iron and steel in Annex II of Regulation (EU) 2023/956 are direct-emissions-only for CBAM unless the legal scope changes."}}
STEEL_72_EXCLUSIONS=("72022","72023000","72025000","72027000","72028000","72029100","72029200","72029300","720299","7204")
STEEL_OTHER_PREFIXES=("26011200","7301","7302","7303","7304","7305","7306","7307","7308","7309","7310","7311")
def normalize_cn(code): return "".join(ch for ch in str(code) if ch.isdigit())
def steel_cbam_scope(cn_code):
 c=normalize_cn(cn_code)
 if c.startswith("72"):
  excluded=any(c.startswith(x) for x in STEEL_72_EXCLUSIONS); return {"in_scope":not excluded,"direct_only":not excluded,"sector":"iron_and_steel","cn":c}
 if any(c.startswith(x) for x in STEEL_OTHER_PREFIXES): return {"in_scope":True,"direct_only":True,"sector":"iron_and_steel","cn":c}
 return {"in_scope":False,"direct_only":False,"sector":None,"cn":c}
def methodology_for(production_date,methodology_id=None):
 d=date.fromisoformat(production_date) if isinstance(production_date,str) else production_date
 if methodology_id:
  m=METHODOLOGIES.get(methodology_id)
  if not m: raise ValueError(f"Unknown methodology: {methodology_id}")
  if d<date.fromisoformat(m["effective_from"]): raise ValueError("Methodology is not effective for production date")
  return m
 candidates=[m for m in METHODOLOGIES.values() if d>=date.fromisoformat(m["effective_from"]) and (not m["effective_to"] or d<=date.fromisoformat(m["effective_to"]))]
 if not candidates: raise ValueError("No CBAM methodology configured for production date")
 return sorted(candidates,key=lambda m:m["effective_from"],reverse=True)[0]
def source_emissions_tco2(activity):
 if activity.get("measured_emissions_tco2") is not None:return float(activity["measured_emissions_tco2"])
 return float(activity.get("quantity") or 0)*float(activity.get("emission_factor_tco2_per_unit") or 0)*float(activity.get("oxidation_factor") if activity.get("oxidation_factor") is not None else 1)*float(activity.get("conversion_factor") if activity.get("conversion_factor") is not None else 1)
def calculate_actual_steel(payload):
 production_date=payload.get("production_date") or f"{payload.get('reporting_period',2026)}-12-31"; method=methodology_for(production_date,payload.get("methodology_id")); scope=steel_cbam_scope(payload["cn_code"])
 if not scope["in_scope"]:raise ValueError(f"CN {payload['cn_code']} is not configured as CBAM iron/steel scope")
 activity_level=float(payload.get("activity_level_t") or 0)
 if activity_level<=0:raise ValueError("activity_level_t must be > 0")
 source_lines=[]; gross_direct=0.0
 for src in payload.get("direct_emission_sources",[]):
  em=source_emissions_tco2(src); gross_direct+=em; source_lines.append({**src,"calculated_emissions_tco2":round(em,9)})
 adjustments=payload.get("boundary_adjustments",[]); adjustment_total=sum(float(x.get("emissions_tco2") or 0) for x in adjustments); attributed=gross_direct+adjustment_total
 precursor_lines=[]; precursor_embedded=default_share_t=precursor_total_t=0.0
 for p in payload.get("precursors",[]):
  qty=float(p.get("quantity_t") or 0); see=float(p.get("specific_embedded_emissions_tco2_per_t") or 0); em=qty*see; precursor_embedded+=em; precursor_total_t+=qty
  if str(p.get("value_type","ACTUAL")).upper()=="DEFAULT":default_share_t+=qty
  precursor_lines.append({**p,"embedded_emissions_tco2":round(em,9)})
 total=attributed+precursor_embedded; electricity=payload.get("electricity",{}); indirect=float(electricity.get("consumption_kwh") or 0)*float(electricity.get("emission_factor_tco2_per_kwh") or 0); included=0.0 if method["steel_indirect_in_scope"] is False else indirect
 checks={"monitoring_plan_ref_present":bool(payload.get("monitoring_plan_ref")),"reporting_period_present":bool(payload.get("reporting_period")),"production_route_present":bool(payload.get("production_route")),"installation_id_present":bool(payload.get("installation_id")),"verifier_status":payload.get("verification",{}).get("status","NOT_PROVIDED")}
 h=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()
 return {"calculation_id":str(uuid4()),"methodology":method,"scope":scope,"input_hash":h,"reporting_period":payload.get("reporting_period"),"installation_id":payload.get("installation_id"),"production_process":payload.get("production_process"),"production_route":payload.get("production_route"),"cn_code":scope["cn"],"activity_level_t":activity_level,"own_direct_emissions_tco2":round(gross_direct,9),"boundary_adjustments_tco2":round(adjustment_total,9),"attributed_own_direct_emissions_tco2":round(attributed,9),"precursor_embedded_emissions_tco2":round(precursor_embedded,9),"total_direct_embedded_emissions_tco2":round(total,9),"specific_direct_embedded_emissions_tco2_per_t":round(total/activity_level,9),"indirect_emissions_audit_tco2":round(indirect,9),"indirect_emissions_included_tco2":round(included,9),"specific_embedded_emissions_tco2_per_t":round((total+included)/activity_level,9),"precursor_default_quantity_share_pct":round(100*default_share_t/precursor_total_t,4) if precursor_total_t else 0.0,"source_lines":source_lines,"precursor_lines":precursor_lines,"boundary_adjustments":adjustments,"controls":checks,"verification_required_for_actual_values":True,"status":"CALCULATED_UNVERIFIED" if str(checks["verifier_status"]).upper()!="VERIFIED" else "CALCULATED_VERIFIED","legal_guardrail":"Calculation arithmetic is versioned to EU 2025/2547. Validity of monitoring plan, system boundary, factors, measurements, precursor evidence and verification must be established by the operator/verifier."}
def persist_calculation(payload):
 result=calculate_actual_steel(payload); now=datetime.now(timezone.utc).isoformat()
 with connect() as conn:
  conn.execute("INSERT INTO cbam_calculations(id,methodology_id,installation_id,reporting_period,cn_code,production_route,activity_level_t,specific_embedded_emissions,payload_json,result_json,input_hash,status,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",(result["calculation_id"],result["methodology"]["id"],result.get("installation_id"),str(result.get("reporting_period") or ""),result["cn_code"],result.get("production_route"),result["activity_level_t"],result["specific_embedded_emissions_tco2_per_t"],json.dumps(payload),json.dumps(result),result["input_hash"],result["status"],now)); audit(conn,None,"cbam.calculated",{"calculation_id":result["calculation_id"],"methodology":result["methodology"]["id"],"status":result["status"]})
 return result
def list_calculations():
 with connect() as conn:return rows(conn,"SELECT id,methodology_id,installation_id,reporting_period,cn_code,production_route,activity_level_t,specific_embedded_emissions,input_hash,status,created_at FROM cbam_calculations ORDER BY created_at DESC")
