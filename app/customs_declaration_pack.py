from __future__ import annotations
from .taric_engine import resolve_taric
from .steel_trade_engine_v2 import evaluate as steel_evaluate
from .cbam_verification_pack import build_pack
from .cbam_engine import steel_cbam_scope
VERSION="EU_CUSTOMS_DECLARATION_READINESS_V1"
def compile_pack(payload):
 required=("shipment_ref","cn_code","origin_country","import_date","customs_value_eur","quantity_t")
 missing=[k for k in required if payload.get(k) in (None,"")]
 if missing:raise ValueError("Missing: "+", ".join(missing))
 taric=resolve_taric(payload["cn_code"],payload["origin_country"],payload["import_date"],payload["customs_value_eur"],payload["quantity_t"],payload.get("customs_documents"),payload.get("taric_additional_code"))
 steel=steel_evaluate(payload)
 cbam_scope=steel_cbam_scope(payload["cn_code"]); cbam_pack=None; blockers=[]
 blockers += [{"engine":"TARIC",**b} for b in taric.get("blockers",[])]
 if steel.get("applicable") is not False and steel.get("status")=="PRODUCT_MAPPING_REQUIRED":blockers += [{"engine":"STEEL",**b} for b in steel.get("blockers",[])]
 if steel.get("entitlement_status")=="QUOTA_BALANCE_REQUIRED":blockers.append({"engine":"STEEL","code":"STEEL_QUOTA_BALANCE","reason":"Current quota balance required."})
 if cbam_scope["in_scope"]:
  cbam_pack=build_pack(payload.get("cbam_verification_pack") or {})
  if not cbam_pack["valid"]:blockers.append({"engine":"CBAM","code":"CBAM_VERIFICATION_PACK","reason":"CBAM verification pack incomplete.","missing":cbam_pack["missing"]})
 docs=sorted(set([b.get("document") for b in taric.get("blockers",[]) if b.get("document")]))
 customs_liability=None
 if taric.get("resolved"):
  customs_liability=round(float(taric.get("total_taric_duty_eur") or 0)+float(steel.get("additional_duty_eur") or 0),2)
 return {"version":VERSION,"shipment_ref":payload["shipment_ref"],"decision":"READY_TO_DECLARE" if not blockers else "BLOCKED","ready_to_declare":not blockers,"taric":taric,"steel_trade_measure":steel,"cbam_verification":cbam_pack,"required_document_codes":docs,"customs_liability_eur":customs_liability,"blockers":blockers,"declaration_fields":{"cn_code":payload["cn_code"],"origin_country":payload["origin_country"],"customs_value_eur":payload["customs_value_eur"],"quantity_t":payload["quantity_t"],"additional_code":payload.get("taric_additional_code"),"documents":payload.get("customs_documents") or []},"guardrail":"READY_TO_DECLARE means Setu's loaded regulatory rules/data/evidence are complete; customs acceptance and quota allocation remain decisions of the competent customs systems/authorities."}
