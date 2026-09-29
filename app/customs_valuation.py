from __future__ import annotations
VERSION="UCC_VALUATION_70_74_V1"
def calculate(p):
 method=int(p.get("method",1)); blockers=[]
 if method==1:
  if p.get("price_paid_or_payable_eur") is None:blockers.append({"code":"VALUATION_TRANSACTION_VALUE_REQUIRED","evidence_type":"COMMERCIAL_INVOICE"});base=float(p.get("price_paid_or_payable_eur") or 0)
  additions=sum(float(p.get(k) or 0) for k in ("buying_commissions_excepted_eur","assists_eur","royalties_eur","resale_proceeds_eur","pre_border_transport_insurance_eur","packing_eur"))
  # buying commissions are excluded under UCC; caller should leave zero. Keep explicit warning if nonzero.
  if float(p.get("buying_commissions_excepted_eur") or 0):blockers.append({"code":"VALUATION_BUYING_COMMISSION_EXCLUDE","reason":"Buying commission must not be added as Article 71 commission."})
  additions-=float(p.get("buying_commissions_excepted_eur") or 0)
  deductions=sum(float(p.get(k) or 0) for k in ("post_entry_transport_eur","post_import_construction_eur","eu_customs_duties_eur","separately_identified_interest_eur"))
  value=base+additions-deductions
  if p.get("related_parties") and not p.get("relationship_did_not_influence_price_evidence"):blockers.append({"code":"VALUATION_RELATED_PARTY_EVIDENCE","evidence_type":"TRANSFER_PRICING_CUSTOMS_SUPPORT"})
 else:
  if method not in (2,3,4,5,6):blockers.append({"code":"VALUATION_METHOD_INVALID"});value=None
  elif p.get("determined_customs_value_eur") is None:blockers.append({"code":"VALUATION_METHOD_EVIDENCE_REQUIRED","method":method,"evidence_type":"CUSTOMS_VALUATION_WORKPAPER"});value=None
  else:value=float(p["determined_customs_value_eur"])
 return {"status":"PASS" if not blockers else "BLOCKED","method":method,"customs_value_eur":round(value,2) if value is not None else None,"blockers":blockers,"rule_version":VERSION,"legal_basis":"UCC Regulation 952/2013 Articles 69-76"}
