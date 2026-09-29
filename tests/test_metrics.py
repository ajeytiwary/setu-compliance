from app.metrics import shipment_score,portfolio_metrics
def test_value_weighted_north_star():
 req_ready=[{"blocking":1,"status":"PASS","required_evidence":1,"evidence_count":1,"label":"x"}]; req_blocked=[{"blocking":1,"status":"MISSING","required_evidence":1,"evidence_count":0,"label":"x"}]; a={"value_eur":900,"manual_hours":2,"supplier_required":1,"supplier_complete":1}; b={"value_eur":100,"manual_hours":8,"supplier_required":1,"supplier_complete":0}; ss=[]
 for x,req in [(a,req_ready),(b,req_blocked)]:ss.append({**x,"score":shipment_score(x,req,None),"verification_cycle_days":None})
 m=portfolio_metrics(ss); assert m["auto_compliance_ready_value_pct"]==90.0; assert m["manual_compliance_hours_per_shipment"]==5.0
