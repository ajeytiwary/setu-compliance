from __future__ import annotations

"""Versioned rules-of-origin engine.

The current EU-India FTA text was published after negotiations concluded on 27 Jan 2026,
but as of 28 Aug 2026 the Commission states it is not yet binding/in force. Therefore this
engine intentionally returns CURRENT_MFN for current shipments.
"""

from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4
import json
from .db import connect, rows, audit

AGREEMENTS={"EU_IN_FTA_2026_NEGOTIATED":{"id":"EU_IN_FTA_2026_NEGOTIATED","parties":["EU","IN"],"status":"NEGOTIATED_NOT_IN_FORCE","negotiations_concluded":"2026-01-27","effective_from":None,"source":"https://policy.trade.ec.europa.eu/eu-trade-relationships-country-and-region/countries-and-regions/india/eu-india-agreements/text-agreements_en","origin_chapter":"Chapter 3 - Rules of Origin and Origin Procedures","proof_model":"statement_on_origin / certification provisions in published negotiated text","warning":"Published texts are for information and may change through legal revision; no preferential claim is available until entry into force."}}

def ncn(code:str)->str: return "".join(ch for ch in str(code) if ch.isdigit())
def tariff_heading(code:str,level:int)->str: return ncn(code)[:level]
def rvc(ex_works_price:float,non_originating_material_value:float)->float:
    if ex_works_price<=0: raise ValueError("ex_works_price must be > 0")
    return 100*(ex_works_price-non_originating_material_value)/ex_works_price
def maxnom(ex_works_price:float,non_originating_material_value:float)->float:
    if ex_works_price<=0: raise ValueError("ex_works_price must be > 0")
    return 100*non_originating_material_value/ex_works_price

def evaluate_psr(rule:dict[str,Any],product:dict[str,Any],materials:list[dict[str,Any]])->dict[str,Any]:
    pcode=ncn(product["hs_code"]); exw=float(product.get("ex_works_price") or 0)
    nonorig=[m for m in materials if not bool(m.get("originating")) and not bool(m.get("cumulated"))]
    nonorig_value=sum(float(m.get("value") or 0) for m in nonorig)
    def primitive(r):
        kind=r["type"].upper()
        if kind=="WO": return {"type":kind,"pass":len(nonorig)==0,"detail":f"non-originating materials={len(nonorig)}"}
        if kind in ("CC","CTH","CTSH"):
            lvl={"CC":2,"CTH":4,"CTSH":6}[kind]
            bad=[m for m in nonorig if tariff_heading(m["hs_code"],lvl)==tariff_heading(pcode,lvl)]
            return {"type":kind,"pass":not bad,"detail":{"level":lvl,"non_originating_same_classification":[m.get("material_id") for m in bad]}}
        if kind=="RVC_MIN":
            value=rvc(exw,nonorig_value); return {"type":kind,"pass":value>=float(r["threshold_pct"]),"value_pct":round(value,4),"threshold_pct":float(r["threshold_pct"])}
        if kind=="MAXNOM":
            value=maxnom(exw,nonorig_value); return {"type":kind,"pass":value<=float(r["threshold_pct"]),"value_pct":round(value,4),"threshold_pct":float(r["threshold_pct"])}
        if kind=="SPECIFIC_PROCESS":
            required=set(r.get("required_processes",[])); actual=set(product.get("processes",[])); missing=sorted(required-actual)
            return {"type":kind,"pass":not missing,"missing_processes":missing}
        raise ValueError(f"Unsupported PSR primitive {kind}")
    if "all_of" in rule:
        parts=[primitive(x) for x in rule["all_of"]]; return {"pass":all(x["pass"] for x in parts),"operator":"ALL","parts":parts}
    if "any_of" in rule:
        parts=[primitive(x) for x in rule["any_of"]]; return {"pass":any(x["pass"] for x in parts),"operator":"ANY","parts":parts}
    return primitive(rule)

def evaluate_origin(payload:dict[str,Any])->dict[str,Any]:
    shipment_date=date.fromisoformat(payload["shipment_date"]); agreement=AGREEMENTS[payload.get("agreement_id","EU_IN_FTA_2026_NEGOTIATED")]
    current_legal=agreement["effective_from"] is not None and shipment_date>=date.fromisoformat(agreement["effective_from"])
    psr=payload.get("product_specific_rule"); preview=evaluate_psr(psr,payload["product"],payload.get("materials",[])) if psr else None
    qualifies=bool(preview and preview.get("pass")); available=bool(current_legal and qualifies)
    normal=float(payload.get("mfn_duty_rate_pct") or 0); pref=float(payload.get("preferential_duty_rate_pct") or 0) if available else normal
    customs=float(payload.get("customs_value_eur") or 0); saving=customs*max(normal-pref,0)/100
    return {"evaluation_id":str(uuid4()),"agreement":agreement,"shipment_date":payload["shipment_date"],"product":payload["product"],"legal_regime":"FTA_IN_FORCE" if current_legal else "CURRENT_MFN","psr_evaluation":preview,"technical_origin_preview":qualifies if psr else None,"preference_available":available,"mfn_duty_rate_pct":normal,"applied_duty_rate_pct":pref,"tariff_saving_eur":round(saving,2),"proof_of_origin_status":"NOT_AVAILABLE_UNDER_FTA_YET" if not current_legal else ("REQUIRED" if available else "NOT_ELIGIBLE"),"guardrail":agreement["warning"]}

def persist_origin_evaluation(payload:dict[str,Any])->dict[str,Any]:
    result=evaluate_origin(payload); now=datetime.now(timezone.utc).isoformat()
    with connect() as conn:
        conn.execute("INSERT INTO origin_evaluations(id,agreement_id,shipment_ref,shipment_date,hs_code,legal_regime,preference_available,tariff_saving_eur,payload_json,result_json,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(result["evaluation_id"],result["agreement"]["id"],payload.get("shipment_ref"),result["shipment_date"],ncn(payload["product"]["hs_code"]),result["legal_regime"],int(result["preference_available"]),result["tariff_saving_eur"],json.dumps(payload),json.dumps(result),now))
        audit(conn,payload.get("shipment_ref"),"origin.evaluated",{"evaluation_id":result["evaluation_id"],"legal_regime":result["legal_regime"],"preference_available":result["preference_available"]})
    return result

def list_origin_evaluations()->list[dict[str,Any]]:
    with connect() as conn: return rows(conn,"SELECT id,agreement_id,shipment_ref,shipment_date,hs_code,legal_regime,preference_available,tariff_saving_eur,created_at FROM origin_evaluations ORDER BY created_at DESC")
