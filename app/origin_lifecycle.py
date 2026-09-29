from __future__ import annotations
VERSION="ORIGIN_LIFECYCLE_V1"
def evaluate(p):
 blockers=[]; non=p.get("non_preferential") or {}; pref=p.get("preferential") or {}
 if not non.get("country"):blockers.append({"code":"NONPREFERENTIAL_ORIGIN_REQUIRED","evidence_type":"ORIGIN_DETERMINATION"})
 if not non.get("basis_ref"):blockers.append({"code":"NONPREFERENTIAL_ORIGIN_BASIS","evidence_type":"ORIGIN_WORKPAPER"})
 claim=bool(pref.get("claim_preference"))
 if claim:
  if pref.get("agreement_status")!="IN_FORCE":blockers.append({"code":"PREFERENCE_NOT_LEGALLY_AVAILABLE"})
  if not pref.get("psr_pass"):blockers.append({"code":"ORIGIN_PSR_NOT_MET","evidence_type":"ORIGIN_CALCULATION"})
  typ=pref.get("proof_type")
  if typ not in ("EUR1","EUR_MED","STATEMENT_ON_ORIGIN","ORIGIN_DECLARATION","IMPORTERS_KNOWLEDGE"):blockers.append({"code":"PROOF_OF_ORIGIN_TYPE_REQUIRED","evidence_type":"PROOF_OF_ORIGIN"})
  if not pref.get("proof_ref"):blockers.append({"code":"PROOF_OF_ORIGIN_REQUIRED","evidence_type":"PROOF_OF_ORIGIN"})
  if typ=="STATEMENT_ON_ORIGIN" and pref.get("rex_required") and not pref.get("rex_number"):blockers.append({"code":"REX_NUMBER_REQUIRED","evidence_type":"REX_REGISTRATION"})
 return {"status":"PASS" if not blockers else "BLOCKED","non_preferential_origin":non.get("country"),"preferential_claim":claim,"blockers":blockers,"rule_version":VERSION}
