from __future__ import annotations
from datetime import date
from .cbam_verification import validate_verification_report
PACK_VERSION="CBAM_VERIFY_2546_2551_V1"
MONITORING_REQUIRED=("version","effective_from","installation_id","production_processes","calculation_methods","system_boundaries","source_streams","data_sources","quality_controls")
OPERATOR_REQUIRED=("reporting_period","installation_id","goods","activity_levels","installation_emissions","production_process_emissions","precursors","heat_waste_gas_electricity_balance","data_gaps")
def _missing(obj,fields,prefix):return [f"{prefix}.{k}" for k in fields if obj.get(k) in (None,"",[])]
def build_pack(payload):
 plan=payload.get("monitoring_plan") or {}; op=payload.get("operator_emissions_report") or {}; vr=payload.get("verification_report") or {}
 missing=_missing(plan,MONITORING_REQUIRED,"monitoring_plan")+_missing(op,OPERATOR_REQUIRED,"operator_emissions_report")
 validation=validate_verification_report(vr); missing+=validation["missing"]
 findings=vr.get("findings") or []; unresolved=[f for f in findings if str(f.get("status","OPEN")).upper() not in ("RESOLVED","CLOSED")]
 verifier=vr.get("verifier") or {}; expiry=verifier.get("accreditation_expiry"); accreditation_current=False
 if expiry:
  try:accreditation_current=date.fromisoformat(expiry)>=date.fromisoformat(str(op.get("reporting_period","2026"))+"-12-31")
  except ValueError:pass
 if not accreditation_current:missing.append("verifier.accreditation_current_for_reporting_period")
 material=[f for f in unresolved if str(f.get("severity","")).upper() in ("MATERIAL_MISSTATEMENT","MATERIAL_NONCONFORMITY","MATERIAL")]
 if material:missing.append("verification_report.unresolved_material_findings")
 state="VERIFIED_REASONABLE_ASSURANCE" if not missing else "BLOCKED"
 return {"pack_version":PACK_VERSION,"state":state,"valid":not missing,"missing":sorted(set(missing)),"unresolved_findings":unresolved,"accreditation_current":accreditation_current,"monitoring_plan":plan,"operator_emissions_report":op,"verification_report":vr,"legal_basis":["Implementing Regulation (EU) 2025/2546","Delegated Regulation (EU) 2025/2551","Implementing Regulation (EU) 2025/2547"],"guardrail":"Schema/readiness validation does not itself accredit a verifier or replace verification performed under EU law."}
