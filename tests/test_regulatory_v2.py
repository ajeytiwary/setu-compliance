from app.regulatory_registry import registry
from app import cbam_definitive_v2 as v2
from app.cbam_verification_pack import build_pack
def test_every_regulation_has_lifecycle_fields():
 r=registry("2026-09-29")
 fields=("legal_basis","version","published_at","effective_from","effective_to","status","jurisdiction","product_scope","source","calculation_version")
 assert all(all(k in x for k in fields) for x in r["regulations"])
 assert all(x["schema_validation"]["valid"] for x in r["regulations"])
def test_cbam_default_markup_and_faa(tmp_path,monkeypatch):
 monkeypatch.setattr(v2,"DATA",tmp_path)
 v2.import_defaults("country,cn_code,production_route,direct,indirect,total\nIN,72083900,C,2,0,2\n")
 v2.import_benchmarks("cn_code,production_route,benchmark\n72083900,C,1.5\n")
 d=v2.select_default("IN","72083900","C",2026); assert d["certificate_default_total"]==2.2
 f=v2.free_allocation_adjustment("72083900",100,2026,"C",1.0); assert f["available"]; assert f["free_allocation_adjustment_tco2e"]==146.25
def test_verification_pack_blocks_material_finding():
 p={"monitoring_plan":{"version":"1","effective_from":"2026-01-01","installation_id":"I","production_processes":["HRC"],"calculation_methods":["mass balance"],"system_boundaries":["BF-BOF"],"source_streams":["coal"],"data_sources":["meter"],"quality_controls":["calibration"]},"operator_emissions_report":{"reporting_period":"2026","installation_id":"I","goods":["HRC"],"activity_levels":[1],"installation_emissions":1,"production_process_emissions":1,"precursors":[],"heat_waste_gas_electricity_balance":{},"data_gaps":[]},"verification_report":{"installation":{"operator_name":"X","operator_registration_number":"R","installation_name":"P","installation_address":"IN","latitude":1,"longitude":1,"reporting_period":"2026"},"verifier":{"verifier_name":"V","verifier_address":"EU","lead_auditor":"A","accreditation_number":"N","national_accreditation_body":"NAB","accreditation_country":"DE","accreditation_expiry":"2027-12-31","accreditation_scope":"CBAM steel"},"monitoring_plan":{"version":"1","production_processes":["HRC"],"calculation_methods":["mass balance"]},"statement":{"reasonable_assurance":True,"free_from_material_misstatements":True,"free_from_material_nonconformities":True},"findings":[{"severity":"MATERIAL","status":"OPEN"}]}}
 r=build_pack(p); assert r["state"]=="BLOCKED"; assert "verification_report.unresolved_material_findings" in r["missing"]
