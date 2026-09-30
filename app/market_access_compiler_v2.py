from __future__ import annotations
from .customs_declaration_pack import compile_pack as base_pack
from .ppwr_engine import evaluate as ppwr
from .reach_scip_engine import evaluate as reach
from .sanctions_engine import screen as sanctions
from .customs_valuation import calculate as valuation
from .origin_lifecycle import evaluate as origin
VERSION="EU_MARKET_ACCESS_COMPILER_V2"
def _evidence_index(items):
 return {str(x.get("evidence_type")):x for x in items or [] if x.get("evidence_type")}
def compile_shipment(p):
 engines={"ppwr":ppwr(p.get("ppwr") or {"placing_on_market_date":p["import_date"]}),"reach_scip":reach(p.get("reach_scip") or {}),"sanctions":sanctions(p.get("sanctions") or {}),"valuation":valuation(p.get("valuation") or {"method":1,"price_paid_or_payable_eur":p.get("customs_value_eur")}),"origin":origin(p.get("origin") or {"non_preferential":{"country":p.get("origin_country")}})}
 # use calculated UCC customs value when complete
 q=dict(p)
 if engines["valuation"].get("customs_value_eur") is not None:q["customs_value_eur"]=engines["valuation"]["customs_value_eur"]
 base=base_pack(q); blockers=list(base["blockers"])
 for name,r in engines.items():
  blockers += [{"engine":name.upper(),**b} for b in r.get("blockers",[])]
 idx=_evidence_index(p.get("evidence"))
 required=[]
 # TARIC codes are declaration-level requirements; evidence mappings can satisfy document refs.
 for code in base.get("required_document_codes",[]):
  match=next((e for e in (p.get("evidence") or []) if code in (e.get("document_codes") or [])),None)
  required.append({"document_code":code,"evidence_id":match.get("id") if match else None,"status":"MAPPED" if match else "MISSING"})
  if not match:blockers.append({"engine":"FILING","code":"TARIC_DOCUMENT_UNMAPPED","document":code,"evidence_type":"CUSTOMS_SUPPORTING_DOCUMENT"})
 for b in list(blockers):
  et=b.get("evidence_type")
  if et and et not in idx:blockers.append({"engine":"EVIDENCE","code":"EVIDENCE_MISSING","evidence_type":et,"for_blocker":b.get("code")})
 refs=sorted(set((p.get("additional_references") or [])+[str(x) for x in p.get("taric_additional_references",[]) ]))
 filing={"shipment_ref":p["shipment_ref"],"declaration_type":p.get("declaration_type","IM"),"procedure_code":p.get("procedure_code"),"cn_code":p["cn_code"],"origin_country":engines["origin"].get("non_preferential_origin") or p["origin_country"],"customs_value_eur":engines["valuation"].get("customs_value_eur"),"gross_mass_kg":p.get("gross_mass_kg"),"net_mass_kg":p.get("net_mass_kg"),"invoice_ref":p.get("invoice_ref"),"transport_document_ref":p.get("transport_document_ref"),"required_documents":required,"additional_references":refs,"evidence_manifest":[{"id":e.get("id"),"type":e.get("evidence_type"),"sha256":e.get("sha256"),"issuer":e.get("issuer"),"valid_until":e.get("valid_until")} for e in p.get("evidence") or []]}
 # dedupe blockers by stable content
 seen=set();ded=[]
 for b in blockers:
  k=(b.get("engine"),b.get("code"),b.get("document"),b.get("evidence_type"),str(b.get("party")),str(b.get("article")))
  if k not in seen:seen.add(k);ded.append(b)
 return {"version":VERSION,"decision":"READY_FOR_SUBMISSION" if not ded else "BLOCKED","ready_for_submission":not ded,"authority_acceptance":"PENDING" if not ded else "NOT_SUBMITTED","filing_pack":filing,"engines":{**engines,"customs":base},"blockers":ded,"guardrail":"READY_FOR_SUBMISSION means EuroSetu rule/evidence gates pass. Customs/CBAM/verifier acceptance remains external."}
