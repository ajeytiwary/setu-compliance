from __future__ import annotations
VERSION="EU_SANCTIONS_OWNERSHIP_V1"
def screen(p):
 blockers=[]; parties=p.get("parties") or []
 for x in parties:
  if x.get("direct_list_match"):blockers.append({"code":"EU_SANCTIONS_DIRECT_MATCH","party":x.get("name"),"evidence_type":"SANCTIONS_SCREEN"})
  owners=x.get("owners") or []; designated=sum(float(o.get("ownership_pct") or 0) for o in owners if o.get("listed"))
  if designated>=50:blockers.append({"code":"EU_SANCTIONS_OWNERSHIP","party":x.get("name"),"listed_ownership_pct":designated,"evidence_type":"UBO_OWNERSHIP"})
  if x.get("controlled_by_listed_person"):blockers.append({"code":"EU_SANCTIONS_CONTROL","party":x.get("name"),"evidence_type":"CONTROL_ASSESSMENT"})
  if not x.get("screened_at") or not x.get("source_version"):blockers.append({"code":"SANCTIONS_SCREEN_FRESHNESS","party":x.get("name"),"evidence_type":"SANCTIONS_SCREEN"})
 return {"status":"PASS" if not blockers else "BLOCKED","blockers":blockers,"rule_version":VERSION,"guardrail":"Ownership >50% and control are separate tests; control remains case-specific."}
