from __future__ import annotations
from datetime import date
SCHEMA_VERSION="REGULATION_LIFECYCLE_V1"
RULES=[
{"id":"EU_CBAM_2023_956","legal_basis":["Regulation (EU) 2023/956"],"version":"2023/956+2025/2083","published_at":"2023-05-16","effective_from":"2026-01-01","effective_to":None,"status":"ACTIVE","jurisdiction":"EU","product_scope":["cement","electricity","fertilisers","iron_and_steel","aluminium","hydrogen"],"source":"https://eur-lex.europa.eu/eli/reg/2023/956/oj","calculation_version":"CBAM_CORE_2026_V1"},
{"id":"EU_CBAM_2025_2547","legal_basis":["Implementing Regulation (EU) 2025/2547"],"version":"2025/2547","published_at":"2025-12-22","effective_from":"2026-01-01","effective_to":None,"status":"ACTIVE","jurisdiction":"EU","product_scope":["CBAM"],"source":"https://eur-lex.europa.eu/eli/reg_impl/2025/2547/oj/eng","calculation_version":"CBAM_METHOD_2547_V2"},
{"id":"EU_CBAM_2025_2620","legal_basis":["Implementing Regulation (EU) 2025/2620"],"version":"2025/2620","published_at":"2025-12-22","effective_from":"2026-01-01","effective_to":None,"status":"ACTIVE","jurisdiction":"EU","product_scope":["CBAM"],"source":"https://eur-lex.europa.eu/eli/reg_impl/2025/2620/oj/eng","calculation_version":"CBAM_FAA_2620_V1"},
{"id":"EU_CBAM_DEFAULTS","legal_basis":["Implementing Regulation (EU) 2025/2621","Implementing Regulation (EU) 2026/1740"],"version":"2025/2621-corrected-2026/1740","published_at":"2026-07-31","effective_from":"2026-01-01","effective_to":None,"status":"ACTIVE","jurisdiction":"EU","product_scope":["CBAM"],"source":"https://eur-lex.europa.eu/eli/reg_impl/2026/1740/oj/eng","calculation_version":"CBAM_DEFAULTS_2621_1740_V1"},
{"id":"EU_CBAM_VERIFICATION","legal_basis":["Implementing Regulation (EU) 2025/2546","Delegated Regulation (EU) 2025/2551"],"version":"2025/2546+2551","published_at":"2025-12-22","effective_from":"2026-01-01","effective_to":None,"status":"ACTIVE","jurisdiction":"EU","product_scope":["CBAM"],"source":"https://eur-lex.europa.eu/eli/reg_impl/2025/2546/oj/eng","calculation_version":"CBAM_VERIFY_2546_2551_V1"},
{"id":"EU_STEEL_2026_1384","legal_basis":["Regulation (EU) 2026/1384"],"version":"2026/1384","published_at":"2026-06-24","effective_from":"2026-07-01","effective_to":None,"status":"ACTIVE","jurisdiction":"EU","product_scope":["steel"],"source":"https://eur-lex.europa.eu/eli/reg/2026/1384/oj","calculation_version":"STEEL_QUOTA_2026_V2"},
{"id":"EU_STEEL_2026_1457","legal_basis":["Implementing Regulation (EU) 2026/1457"],"version":"2026/1457","published_at":"2026-06-30","effective_from":"2026-07-01","effective_to":"2026-12-31","status":"ACTIVE","jurisdiction":"EU","product_scope":["steel"],"source":"https://eur-lex.europa.eu/eli/reg_impl/2026/1457/oj/eng","calculation_version":"STEEL_QUOTA_2026_V2"},
{"id":"EU_INDIA_FTA_2026_NEGOTIATED","legal_basis":["EU-India FTA negotiated text"],"version":"negotiated-2026","published_at":"2026-01-27","effective_from":None,"effective_to":None,"status":"NEGOTIATED_NOT_IN_FORCE","jurisdiction":"EU-India","product_scope":["origin","tariff_preference"],"source":"https://policy.trade.ec.europa.eu/eu-trade-relationships-country-and-region/countries-and-regions/india/eu-india-agreements/text-agreements_en","calculation_version":"FTA_SCENARIO_2026_V1"}]
REQUIRED=("legal_basis","version","published_at","effective_from","effective_to","status","jurisdiction","product_scope","source","calculation_version")
def validate_rule(r):
 missing=[k for k in REQUIRED if k not in r]; return {"valid":not missing,"missing":missing}
def registry(as_of=None):
 d=date.fromisoformat(as_of) if as_of else date.today(); out=[]
 for r in RULES:
  active=r["status"]=="ACTIVE" and r["effective_from"] is not None and d>=date.fromisoformat(r["effective_from"]) and (r["effective_to"] is None or d<=date.fromisoformat(r["effective_to"]))
  out.append({**r,"schema_version":SCHEMA_VERSION,"active_on_date":active,"claimable":active,"schema_validation":validate_rule(r)})
 return {"schema_version":SCHEMA_VERSION,"as_of":d.isoformat(),"regulations":out}
def rule(rule_id,as_of=None):
 return next((r for r in registry(as_of)["regulations"] if r["id"]==rule_id),None)
