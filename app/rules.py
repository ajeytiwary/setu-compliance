from __future__ import annotations
from dataclasses import dataclass
@dataclass(frozen=True)
class Rule:
 code:str; label:str; category:str; blocking:bool; required_evidence:int
STEEL_EU_RULES=[Rule("IDENTITY","Product identity & CN classification","Trade",True,1),Rule("GENEALOGY","Heat/slab/coil genealogy","Traceability",True,2),Rule("CBAM_ACTIVITY","CBAM installation/activity data","CBAM",True,3),Rule("CBAM_EMISSIONS","Embedded emissions calculation","CBAM",True,3),Rule("CBAM_VERIFICATION","Accredited verification for actual emissions","CBAM",True,1),Rule("SUPPLIER_DATA","Required supplier data coverage","Supply chain",True,1),Rule("DPP_ID","DPP unique product identifier","ESPR readiness",False,1),Rule("DPP_MATERIAL","Material/recycled-content data","ESPR readiness",False,2),Rule("DPP_TECH","Technical product data","ESPR readiness",False,1)]
def initial_status(rule,shipment):
 if rule.code=="IDENTITY":return "PASS" if shipment.get("cn_code") and shipment.get("product") else "MISSING"
 if rule.code=="SUPPLIER_DATA":
  req=int(shipment.get("supplier_required") or 0); comp=int(shipment.get("supplier_complete") or 0); return "PASS" if req==0 or comp>=req else "MISSING"
 if rule.code=="CBAM_EMISSIONS":return "PASS" if shipment.get("embedded_emissions_tco2e_per_t") is not None else "MISSING"
 return "MISSING"
