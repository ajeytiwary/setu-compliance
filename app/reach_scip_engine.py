from __future__ import annotations
VERSION="REACH_SCIP_V1"
def evaluate(p):
 blockers=[]; articles=p.get("articles") or []
 if not articles:return {"status":"BLOCKED","blockers":[{"code":"REACH_ARTICLE_BOM_REQUIRED","evidence_type":"ARTICLE_BOM"}],"rule_version":VERSION}
 for a in articles:
  for s in a.get("candidate_list_substances",[]):
   c=s.get("concentration_w_w_pct")
   if c is None:blockers.append({"code":"REACH_SVHC_CONCENTRATION_REQUIRED","article":a.get("id"),"substance":s.get("name"),"evidence_type":"SVHC_DECLARATION"});continue
   if float(c)>0.1:
    if not a.get("article33_safe_use_information_ref"):blockers.append({"code":"REACH_ARTICLE33_INFORMATION","article":a.get("id"),"evidence_type":"ARTICLE33_SAFE_USE"})
    if not a.get("scip_notification_ref"):blockers.append({"code":"SCIP_NOTIFICATION_REQUIRED","article":a.get("id"),"evidence_type":"SCIP_NOTIFICATION"})
 return {"status":"PASS" if not blockers else "BLOCKED","blockers":blockers,"rule_version":VERSION,"legal_basis":["Regulation (EC) 1907/2006 REACH","Directive 2008/98/EC Article 9(1)(i) / SCIP"]}
