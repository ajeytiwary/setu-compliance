from app import eu_public_data as pub
from app.taric_engine import resolve_taric
def _load(tmp_path,monkeypatch,taric,quota=None):
 monkeypatch.setattr(pub,"CACHE",tmp_path)
 pub.store_snapshot("taric",pub.parse_csv(taric,"taric","2026-09-29"),taric.encode())
 if quota:pub.store_snapshot("quota",pub.parse_csv(quota,"quota","2026-09-29"),quota.encode())
def test_taric_stacks_base_and_trade_defence(tmp_path,monkeypatch):
 taric="cn_code,origin_country,measure_type,duty_rate,valid_from\n72083900,IN,THIRD_COUNTRY_DUTY,5%,2026-01-01\n72083900,IN,ANTIDUMPING,10%,2026-01-01\n"
 _load(tmp_path,monkeypatch,taric)
 r=resolve_taric("72083900","IN","2026-09-29",100000,100)
 assert r["resolved"]; assert r["base_customs_duty_eur"]==5000; assert r["trade_defence_duty_eur"]==10000; assert r["total_taric_duty_eur"]==15000
def test_suspension_does_not_remove_antidumping(tmp_path,monkeypatch):
 taric="cn_code,origin_country,measure_type,duty_rate\n72083900,IN,THIRD_COUNTRY_DUTY,5%\n72083900,IN,AUTONOMOUS_SUSPENSION,0%\n72083900,IN,ANTIDUMPING,10%\n"
 _load(tmp_path,monkeypatch,taric); r=resolve_taric("72083900","IN","2026-09-29",100000,100)
 assert r["base_customs_duty_eur"]==0; assert r["trade_defence_duty_eur"]==10000
def test_quota_applies_reduced_rate_only_to_available_quantity(tmp_path,monkeypatch):
 taric="cn_code,origin_country,measure_type,duty_rate,quota_order_number\n72191100,IN,THIRD_COUNTRY_DUTY,5%,\n72191100,IN,TARIFF_QUOTA,0%,09.9862\n"
 quota="order_number,balance_t\n09.9862,40\n"; _load(tmp_path,monkeypatch,taric,quota)
 r=resolve_taric("72191100","IN","2026-09-29",100000,100)
 assert r["resolved"]; assert r["base_customs_duty_eur"]==3000
def test_missing_document_blocks_measure(tmp_path,monkeypatch):
 taric="cn_code,origin_country,measure_type,duty_rate,required_document,condition_text\n72083900,IN,THIRD_COUNTRY_DUTY,5%,C999,Authorisation required\n"
 _load(tmp_path,monkeypatch,taric); r=resolve_taric("72083900","IN","2026-09-29",100000,100)
 assert not r["resolved"]; assert r["blockers"][0]["document"]=="C999"
def test_stale_taric_fails_closed(tmp_path,monkeypatch):
 monkeypatch.setattr(pub,"CACHE",tmp_path); csv="cn_code,origin_country,measure_type,duty_rate\n72083900,IN,THIRD_COUNTRY_DUTY,5%\n"
 pub.store_snapshot("taric",pub.parse_csv(csv,"taric","2026-09-20"),csv.encode())
 assert resolve_taric("72083900","IN","2026-09-29",100000,100)["status"]=="TARIC_SNAPSHOT_REQUIRED"
