from __future__ import annotations
from .cbam_engine import steel_cbam_scope
from .steel_trade_measure import evaluate_steel_entitlement,category_for_cn
from .eu_public_data import quota_balance
CBAM_LEGAL={"status":"ACTIVE","effective_from":"2026-01-01","mass_threshold_t_per_importer_calendar_year":50.0,"source":"https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism/cbam-definitive-regime_en"}
EU_INDIA_FTA={"status":"NEGOTIATED_NOT_IN_FORCE","preference_claimable":False,"source":"https://policy.trade.ec.europa.eu/eu-trade-relationships-country-and-region/countries-and-regions/india/eu-india-agreements/text-agreements_en"}
def compile_active_entitlement(payload):
 required=("cn_code","origin_country","import_date","customs_value_eur","quantity_t")
 missing=[x for x in required if payload.get(x) in (None,"")]
 if missing:raise ValueError("Missing: "+", ".join(missing))
 cat=category_for_cn(payload["cn_code"]); q_remaining=payload.get("steel_quota_remaining_t"); q_asof=payload.get("quota_balance_as_of"); public_quota=None
 if q_remaining is None and cat and cat.get("india_order_number") and str(payload["origin_country"]).upper()=="IN":
  public_quota=quota_balance(cat["india_order_number"],1,payload["import_date"])
  if public_quota.get("available"):
   q_remaining=public_quota["record"]["balance_t"]; q_asof=public_quota["source"]["as_of"]
 steel=evaluate_steel_entitlement(payload["cn_code"],payload["origin_country"],payload["import_date"],payload["customs_value_eur"],payload["quantity_t"],q_remaining,q_asof)
 if public_quota:steel["public_quota_lookup"]=public_quota
 cbam_scope=steel_cbam_scope(payload["cn_code"]); annual=float(payload.get("importer_cbam_mass_ytd_t") or 0)+float(payload["quantity_t"]); cbam_threshold=annual>CBAM_LEGAL["mass_threshold_t_per_importer_calendar_year"]
 cbam={"legal_status":"ACTIVE","in_scope_goods":cbam_scope["in_scope"],"annual_mass_after_shipment_t":annual,"threshold_t":50.0,"authorised_declarant_required":bool(cbam_scope["in_scope"] and cbam_threshold),"embedded_emissions_required":bool(cbam_scope["in_scope"] and cbam_threshold),"legal_basis":CBAM_LEGAL}
 fta={"agreement":"EU-India FTA","legal_status":EU_INDIA_FTA["status"],"preference_claimable":False,"tariff_preference_applied":False,"reason":"Published negotiated text is not binding until entry into force; Setu will not assert a preferential customs entitlement before then.","legal_basis":EU_INDIA_FTA}
 blockers=[]
 if steel.get("applicable") and steel.get("entitlement_status")=="QUOTA_BALANCE_REQUIRED":blockers.append({"code":"STEEL_QUOTA_BALANCE","blocking":True,"reason":"Refresh/supply current EU QUOTA balance before claiming in-quota treatment."})
 if cbam["authorised_declarant_required"] and not payload.get("authorised_cbam_declarant",False):blockers.append({"code":"CBAM_DECLARANT_AUTHORISATION","blocking":True,"reason":"Importer exceeds the 50 t CBAM threshold and authorised declarant status is not confirmed."})
 if cbam["embedded_emissions_required"] and not payload.get("cbam_emissions_verified",False):blockers.append({"code":"CBAM_VERIFIED_EMISSIONS","blocking":True,"reason":"Verified actual emissions or applicable lawful default-value treatment is required for the definitive regime workflow."})
 return {"active_compliance_entitlement":len(blockers)==0,"decision":"ENTITLED" if not blockers else "BLOCKED","shipment_ref":payload.get("shipment_ref"),"steel_measure":steel,"cbam":cbam,"fta":fta,"blockers":blockers,"guardrail":"Active entitlement means Setu's rule conditions are satisfied from supplied/current public data and evidence; customs authorities remain authoritative for acceptance/allocation."}
