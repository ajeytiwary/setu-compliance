from app.cbam_verification import verification_state
from app.regulatory_registry import registry
def test_verification_fails_closed():
 r=verification_state({"installation":{"operator_name":"X"}}); assert r["state"]=="INCOMPLETE"; assert "statement.reasonable_assurance" in r["missing"]
def test_complete_reasonable_assurance_report():
 report={"installation":{"operator_name":"X","operator_registration_number":"R","installation_name":"Plant","installation_address":"India","latitude":15.1,"longitude":76.1,"reporting_period":"2026"},"verifier":{"verifier_name":"V","verifier_address":"EU","lead_auditor":"A","accreditation_number":"N","national_accreditation_body":"NAB","accreditation_country":"DE","accreditation_expiry":"2027-01-01","accreditation_scope":"CBAM steel"},"monitoring_plan":{"version":"1","production_processes":["HRC"],"calculation_methods":["mass balance"]},"statement":{"reasonable_assurance":True,"free_from_material_misstatements":True,"free_from_material_nonconformities":True}}
 assert verification_state(report)["state"]=="VERIFIED_REASONABLE_ASSURANCE"
def test_regulatory_registry_does_not_activate_fta():
 r=registry("2026-09-29"); f=next(x for x in r["regulations"] if x["id"]=="EU_INDIA_FTA_2026_NEGOTIATED"); assert f["claimable"] is False
 steel=next(x for x in r["regulations"] if x["id"]=="EU_STEEL_2026_1384"); assert steel["claimable"] is True
