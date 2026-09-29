import json
from app import eu_public_data as pub
from app.compliance_entitlement import compile_active_entitlement
def test_quota_snapshot_drives_active_entitlement(tmp_path,monkeypatch):
 monkeypatch.setattr(pub,"CACHE",tmp_path)
 csv="order_number,balance_t,initial_volume_t,critical,status,last_allocation_date\n09.9862,100,6504.78,false,OPEN,2026-09-29\n"
 pub.store_snapshot("quota",pub.parse_csv(csv,"quota","2026-09-29"),csv.encode())
 # category 8 has official India order number 09.9862 in the checked-in legal snapshot
 r=compile_active_entitlement({"cn_code":"72191100","origin_country":"IN","import_date":"2026-09-29","customs_value_eur":100000,"quantity_t":20,"importer_cbam_mass_ytd_t":0,"authorised_cbam_declarant":True,"cbam_emissions_verified":True})
 assert r["steel_measure"]["entitlement_status"]=="IN_QUOTA"
 assert r["steel_measure"]["quota_remaining_t"]==100
 assert r["steel_measure"]["public_quota_lookup"]["source"]["source"]=="EU_COMMISSION_QUOTA"
def test_stale_quota_does_not_create_entitlement(tmp_path,monkeypatch):
 monkeypatch.setattr(pub,"CACHE",tmp_path)
 csv="order_number,balance_t\n09.9862,100\n"; pub.store_snapshot("quota",pub.parse_csv(csv,"quota","2026-09-20"),csv.encode())
 r=compile_active_entitlement({"cn_code":"72191100","origin_country":"IN","import_date":"2026-09-29","customs_value_eur":100000,"quantity_t":20,"importer_cbam_mass_ytd_t":0})
 assert r["decision"]=="BLOCKED"; assert r["steel_measure"]["entitlement_status"]=="QUOTA_BALANCE_REQUIRED"
 assert r["steel_measure"]["public_quota_lookup"]["freshness"]["fresh"] is False
def test_taric_normalization_and_provenance(tmp_path,monkeypatch):
 monkeypatch.setattr(pub,"CACHE",tmp_path)
 csv="cn_code,origin_country,measure_type,duty_rate,quota_order_number\n72191100,IN,TARIFF_QUOTA,0,09.9862\n"
 s=pub.store_snapshot("taric",pub.parse_csv(csv,"taric","2026-09-29"),csv.encode())
 assert s["records"][0]["cn_code"]=="72191100"; assert len(s["sha256"])==64
