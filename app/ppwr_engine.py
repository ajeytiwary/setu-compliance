from __future__ import annotations
from datetime import date
VERSION="PPWR_2025_40_V1"; EFFECTIVE=date(2026,8,12)
def evaluate(p):
 d=date.fromisoformat(p["placing_on_market_date"]); blockers=[]; evidence=[]
 if d<EFFECTIVE:return {"applicable":False,"status":"NOT_YET_APPLICABLE","blockers":[],"rule_version":VERSION}
 if not p.get("packaging_components"):blockers.append({"code":"PPWR_PACKAGING_COMPOSITION","evidence_type":"PACKAGING_BOM"})
 for x in p.get("packaging_components",[]):
  if x.get("heavy_metals_mg_kg") is None:blockers.append({"code":"PPWR_HEAVY_METALS_EVIDENCE","component":x.get("id"),"evidence_type":"PACKAGING_CHEMICAL_TEST"})
  elif float(x["heavy_metals_mg_kg"])>100:blockers.append({"code":"PPWR_HEAVY_METALS_LIMIT","component":x.get("id")})
  if x.get("food_contact"):
   vals=x.get("pfas_ppb") or {}
   if vals.get("targeted_single") is None or vals.get("targeted_sum") is None:blockers.append({"code":"PPWR_PFAS_EVIDENCE","component":x.get("id"),"evidence_type":"PFAS_TEST"})
   elif float(vals["targeted_single"])>=25 or float(vals["targeted_sum"])>=250:blockers.append({"code":"PPWR_PFAS_LIMIT","component":x.get("id")})
 if not p.get("conformity_document_ref"):blockers.append({"code":"PPWR_CONFORMITY_EVIDENCE","evidence_type":"PPWR_CONFORMITY"})
 return {"applicable":True,"status":"PASS" if not blockers else "BLOCKED","blockers":blockers,"rule_version":VERSION,"legal_basis":"Regulation (EU) 2025/40","effective_from":"2026-08-12"}
