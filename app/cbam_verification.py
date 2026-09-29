from __future__ import annotations
REQUIRED_INSTALLATION=("operator_name","operator_registration_number","installation_name","installation_address","latitude","longitude","reporting_period")
REQUIRED_VERIFIER=("verifier_name","verifier_address","lead_auditor","accreditation_number","national_accreditation_body","accreditation_country","accreditation_expiry","accreditation_scope")
def validate_verification_report(report):
 missing=[]
 inst=report.get("installation") or {}; verifier=report.get("verifier") or {}; plan=report.get("monitoring_plan") or {}; statement=report.get("statement") or {}
 for k in REQUIRED_INSTALLATION:
  if inst.get(k) in (None,""):missing.append("installation."+k)
 for k in REQUIRED_VERIFIER:
  if verifier.get(k) in (None,""):missing.append("verifier."+k)
 for k in ("version","production_processes","calculation_methods"):
  if plan.get(k) in (None,"",[]):missing.append("monitoring_plan."+k)
 if statement.get("reasonable_assurance") is not True:missing.append("statement.reasonable_assurance")
 if statement.get("free_from_material_misstatements") is not True:missing.append("statement.free_from_material_misstatements")
 if statement.get("free_from_material_nonconformities") is not True:missing.append("statement.free_from_material_nonconformities")
 return {"schema":"EU_CBAM_VERIFICATION_2025_2546","legal_status":"ACTIVE","effective_from":"2026-01-01","valid":not missing,"missing":missing,"registry_template_required":True,"legal_basis":["Commission Implementing Regulation (EU) 2025/2546","Commission Delegated Regulation (EU) 2025/2551"]}
def verification_state(report):
 v=validate_verification_report(report)
 if not v["valid"]:return {**v,"state":"INCOMPLETE"}
 return {**v,"state":"VERIFIED_REASONABLE_ASSURANCE"}
