from app.ppwr_engine import evaluate as ppwr
from app.reach_scip_engine import evaluate as reach
from app.sanctions_engine import screen
from app.customs_valuation import calculate
from app.origin_lifecycle import evaluate as origin
def test_ppwr_applies_and_blocks_missing_packaging_evidence():
 r=ppwr({"placing_on_market_date":"2026-09-29"});assert r["status"]=="BLOCKED"
def test_reach_scip_article_threshold():
 r=reach({"articles":[{"id":"a","candidate_list_substances":[{"name":"SVHC","concentration_w_w_pct":0.2}]}]});assert any(x["code"]=="SCIP_NOTIFICATION_REQUIRED" for x in r["blockers"])
def test_sanctions_ownership_and_control():
 r=screen({"parties":[{"name":"X","screened_at":"2026-09-29","source_version":"v","owners":[{"listed":True,"ownership_pct":51}]}]});assert r["status"]=="BLOCKED"
def test_customs_valuation_transaction_adjustments():
 r=calculate({"method":1,"price_paid_or_payable_eur":100,"assists_eur":10,"pre_border_transport_insurance_eur":5,"post_entry_transport_eur":2});assert r["customs_value_eur"]==113
def test_preference_cannot_activate_without_in_force_agreement():
 r=origin({"non_preferential":{"country":"IN","basis_ref":"B"},"preferential":{"claim_preference":True,"agreement_status":"NEGOTIATED_NOT_IN_FORCE","psr_pass":True,"proof_type":"STATEMENT_ON_ORIGIN","proof_ref":"P"}});assert r["status"]=="BLOCKED"
