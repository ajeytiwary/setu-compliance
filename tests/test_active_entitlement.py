from app.steel_trade_measure import category_for_cn,evaluate_steel_entitlement
from app.compliance_entitlement import compile_active_entitlement
from app import eu_public_data as pub
def test_official_steel_category_1a_mapping():
 c=category_for_cn("7208 39 00"); assert c["category"]=="1A"; assert c["annual_quota_t"]==5198754
def test_active_measure_fails_closed_without_live_balance():
 r=evaluate_steel_entitlement("72083900","IN","2026-09-29",2810000,4100); assert r["legal_status"]=="ACTIVE"; assert r["entitlement_status"]=="QUOTA_BALANCE_REQUIRED"; assert r["additional_duty_eur"] is None
def test_out_of_quota_duty_uses_50_percent_only_on_excess():
 r=evaluate_steel_entitlement("72083900","IN","2026-09-29",100000,100,40,"2026-09-29"); assert r["in_quota_quantity_t"]==40; assert r["out_of_quota_quantity_t"]==60; assert r["additional_duty_eur"]==30000
def test_end_to_end_active_entitlement(tmp_path,monkeypatch):
 monkeypatch.setattr(pub,"CACHE",tmp_path)
 csv="cn_code,origin_country,measure_type,duty_rate\\n72083900,IN,THIRD_COUNTRY_DUTY,0%\\n"
 pub.store_snapshot("taric",pub.parse_csv(csv,"taric","2026-09-29"),csv.encode())
 p={"shipment_ref":"LIVE-1","cn_code":"72083900","origin_country":"IN","import_date":"2026-09-29","customs_value_eur":100000,"quantity_t":20,"steel_quota_remaining_t":1000,"quota_balance_as_of":"2026-09-29","importer_cbam_mass_ytd_t":40,"authorised_cbam_declarant":True,"cbam_emissions_verified":True}
 r=compile_active_entitlement(p); assert r["decision"]=="ENTITLED"; assert r["steel_measure"]["entitlement_status"]=="IN_QUOTA"; assert r["cbam"]["authorised_declarant_required"] is True; assert r["fta"]["preference_claimable"] is False
def test_cbam_authorisation_blocks_above_threshold(tmp_path,monkeypatch):
 monkeypatch.setattr(pub,"CACHE",tmp_path)
 csv="cn_code,origin_country,measure_type,duty_rate\\n72083900,IN,THIRD_COUNTRY_DUTY,0%\\n"
 pub.store_snapshot("taric",pub.parse_csv(csv,"taric","2026-09-29"),csv.encode())
 p={"cn_code":"72083900","origin_country":"IN","import_date":"2026-09-29","customs_value_eur":100000,"quantity_t":20,"steel_quota_remaining_t":1000,"importer_cbam_mass_ytd_t":40,"authorised_cbam_declarant":False,"cbam_emissions_verified":True}
 r=compile_active_entitlement(p); assert r["decision"]=="BLOCKED"; assert any(x["code"]=="CBAM_DECLARANT_AUTHORISATION" for x in r["blockers"])
