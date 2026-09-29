from __future__ import annotations
from datetime import date
REGULATIONS=[
{"id":"EU_CBAM_2023_956","name":"Carbon Border Adjustment Mechanism","status":"ACTIVE","effective_from":"2026-01-01","source":"https://eur-lex.europa.eu/eli/reg/2023/956/oj","jurisdiction":"EU","scope":["iron_and_steel","aluminium","cement","fertilisers","hydrogen","electricity"]},
{"id":"EU_CBAM_2025_2547","name":"CBAM embedded-emissions methodology","status":"ACTIVE","effective_from":"2026-01-01","source":"https://eur-lex.europa.eu/eli/reg_impl/2025/2547/oj/eng","jurisdiction":"EU","scope":["CBAM"]},
{"id":"EU_CBAM_2025_2546","name":"CBAM verification principles/report","status":"ACTIVE","effective_from":"2026-01-01","source":"https://eur-lex.europa.eu/eli/reg_impl/2025/2546/oj/eng","jurisdiction":"EU","scope":["CBAM"]},
{"id":"EU_STEEL_2026_1384","name":"EU steel tariff quota measure","status":"ACTIVE","effective_from":"2026-07-01","source":"https://eur-lex.europa.eu/eli/reg/2026/1384/oj","jurisdiction":"EU","scope":["steel"]},
{"id":"EU_STEEL_2026_1457","name":"2026 steel quota distribution","status":"ACTIVE","effective_from":"2026-07-01","effective_to":"2026-12-31","source":"https://eur-lex.europa.eu/eli/reg_impl/2026/1457/oj/eng","jurisdiction":"EU","scope":["steel"]},
{"id":"EU_INDIA_FTA_2026_NEGOTIATED","name":"EU-India FTA negotiated text","status":"NEGOTIATED_NOT_IN_FORCE","effective_from":None,"source":"https://policy.trade.ec.europa.eu/eu-trade-relationships-country-and-region/countries-and-regions/india/eu-india-agreements/text-agreements_en","jurisdiction":"EU-India","scope":["origin","tariff_preference"]}]
def registry(as_of=None):
 d=date.fromisoformat(as_of) if as_of else date.today()
 out=[]
 for r in REGULATIONS:
  active=r["status"]=="ACTIVE" and (not r.get("effective_from") or d>=date.fromisoformat(r["effective_from"])) and (not r.get("effective_to") or d<=date.fromisoformat(r["effective_to"]))
  out.append({**r,"active_on_date":active,"claimable":active})
 return {"as_of":d.isoformat(),"regulations":out}
