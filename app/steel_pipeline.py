from __future__ import annotations
import json
from typing import Any
from .db import connect,rows
from .cbam_engine import calculate_actual_steel
from .fta_origin import evaluate_origin

def _canonical(conn,connector):
    out=[]
    for r in rows(conn,"SELECT id,source_key,payload_json,sha256,created_at FROM canonical_records WHERE connector=? ORDER BY created_at DESC",(connector,)):
        d=json.loads(r["payload_json"]); d.update({"_canonical_id":r["id"],"_source_key":r["source_key"],"_sha256":r["sha256"]}); out.append(d)
    return out

def assemble_shipment(shipment_ref):
    with connect() as conn:
        sap=[x for x in _canonical(conn,"sap_sd") if x.get("shipment_id")==shipment_ref]
        if not sap:raise ValueError(f"No canonical SAP SD record for {shipment_ref}")
        s=sap[0]; batch=s.get("batch_id"); mes=_canonical(conn,"mes")
        genealogy=[x for x in mes if x.get("child_id")==batch or x.get("parent_id")==batch]
        parents={x.get("parent_id") for x in genealogy}; genealogy += [x for x in mes if x.get("child_id") in parents and x not in genealogy]
        facility=(genealogy[0].get("facility") if genealogy else None) or "UNKNOWN"
        ems=[x for x in _canonical(conn,"ems_activity") if x.get("facility")==facility]
        # Prefer shipment-specific activity rows (source_id carries the shipment
        # ref, e.g. SRC-BF-BOF-JSW-HRC-NL-001) over the whole-facility ledger so
        # per-shipment CBAM math does not sum every shipment's activity.
        scoped=[x for x in ems if shipment_ref in str(x.get("source_id") or "")]
        if scoped:ems=scoped
        preferred=[x for x in ems if x.get("process")=="Integrated-HRC"]
        if preferred:ems=preferred
        suppliers=_canonical(conn,"supplier_cbam"); verifiers=_canonical(conn,"verifier")
        # Shipment-scoped verifier records (verifier.csv may carry an optional
        # shipment_id) take precedence: if any exist, only the ones matching
        # this shipment apply. Otherwise installation-level records (no
        # shipment_id) apply to all shipments at that installation.
        if any(x.get("shipment_id") for x in verifiers):
            verifiers=[x for x in verifiers if x.get("shipment_id")==shipment_ref]
        return {"shipment":s,"genealogy":genealogy,"activity":ems,"supplier_precursors":suppliers,"verifications":verifiers,"provenance":{"sap_sd":[x["_sha256"] for x in sap],"mes":[x["_sha256"] for x in genealogy],"ems":[x["_sha256"] for x in ems],"supplier_cbam":[x["_sha256"] for x in suppliers],"verifier":[x["_sha256"] for x in verifiers]},"completeness":{"sap":bool(sap),"genealogy":bool(genealogy),"ems":bool(ems),"supplier_precursors":bool(suppliers),"verifier":bool(verifiers)}}

def build_cbam_payload(shipment_ref):
    a=assemble_shipment(shipment_ref); s=a["shipment"]
    direct=[{"source_id":x.get("source_id"),"activity_type":x.get("activity_type"),"quantity":x.get("quantity"),"unit":x.get("unit"),"measured_emissions_tco2":x.get("measured_emissions_tco2"),"emission_factor_tco2_per_unit":x.get("emission_factor_tco2_per_unit"),"oxidation_factor":x.get("oxidation_factor"),"conversion_factor":x.get("conversion_factor"),"measurement_method":x.get("measurement_method"),"evidence_hash":x.get("_sha256")} for x in a["activity"]]
    prec=[{"precursor_cn":p.get("precursor_cn"),"name":p.get("precursor_name"),"quantity_t":float(p.get("quantity_t") or 0),"specific_embedded_emissions_tco2_per_t":float(p["specific_embedded_emissions"]),"value_type":"ACTUAL" if str(p.get("verification_status")).upper()=="VERIFIED" else "DEFAULT","installation_id":p.get("installation_id"),"verification_status":p.get("verification_status"),"evidence_ref":p.get("evidence_ref"),"evidence_hash":p.get("_sha256")} for p in a["supplier_precursors"] if p.get("specific_embedded_emissions") is not None]
    verified=any(str(v.get("status")).upper()=="VERIFIED" for v in a["verifications"]); production_date=(a["genealogy"][0].get("event_time","2026-01-01")[:10] if a["genealogy"] else "2026-01-01")
    route="BF-BOF" if any(str(x.get("process")).upper()=="BOF" for x in a["genealogy"]) else "UNKNOWN"; installation=a["activity"][0].get("facility") if a["activity"] else "UNKNOWN"
    return {"methodology_id":"EU_CBAM_2026_2547","reporting_period":int(production_date[:4]),"production_date":production_date,"installation_id":installation,"monitoring_plan_ref":"PRIVATE_REQUIRED","production_process":"Integrated-HRC","production_route":route,"cn_code":s.get("cn_code"),"activity_level_t":float(s.get("quantity_t") or 0),"direct_emission_sources":direct,"boundary_adjustments":[],"precursors":prec,"verification":{"status":"VERIFIED" if verified else "NOT_PROVIDED"},"_pipeline_provenance":a["provenance"]}

def evaluate_shipment_cbam(shipment_ref):
    asm = assemble_shipment(shipment_ref)
    if not asm["completeness"]["genealogy"] or not asm["completeness"]["ems"]:
        missing = [k for k, v in asm["completeness"].items() if not v]
        return {"status": "BLOCKED_MISSING_CANONICAL_INPUTS", "shipment_ref": shipment_ref,
                "missing": missing, "completeness": asm["completeness"],
                "cbam_payload": None, "result": None}
    payload=build_cbam_payload(shipment_ref); unusable=[x for x in payload["direct_emission_sources"] if x.get("measured_emissions_tco2") is None and x.get("emission_factor_tco2_per_unit") is None]
    if unusable:return {"status":"BLOCKED_MISSING_EMISSION_FACTORS_OR_MEASUREMENTS","shipment_ref":shipment_ref,"cbam_payload":payload,"missing_sources":[x.get("source_id") for x in unusable]}
    result=calculate_actual_steel(payload); return {"status":result["status"],"shipment_ref":shipment_ref,"cbam_payload":payload,"result":result}

def evaluate_shipment_origin(shipment_ref,psr=None):
    a=assemble_shipment(shipment_ref); s=a["shipment"]
    with connect() as conn:mm=_canonical(conn,"sap_mm")
    materials=[{"material_id":m.get("material_id"),"hs_code":m.get("hs_code",""),"value":float(m.get("value_eur") or 0),"originating":str(m.get("country_of_origin")).upper()=="IN"} for m in mm]
    payload={"agreement_id":"EU_IN_FTA_2026_NEGOTIATED","shipment_ref":shipment_ref,"shipment_date":"2026-08-28","customs_value_eur":float(s.get("value_eur") or 0),"mfn_duty_rate_pct":0,"preferential_duty_rate_pct":0,"product":{"hs_code":s.get("cn_code"),"ex_works_price":float(s.get("value_eur") or 0),"processes":[x.get("process") for x in a["genealogy"]]},"materials":materials,"product_specific_rule":psr}
    return {"status":"CURRENT_MFN","shipment_ref":shipment_ref,"input_completeness":{"bom_materials":bool(materials),"published_psr_supplied":bool(psr)},"result":evaluate_origin(payload)}
