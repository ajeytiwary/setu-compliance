from __future__ import annotations
from statistics import median
def shipment_score(shipment,requirements,verification=None):
 blocking=[r for r in requirements if r["blocking"]]; nonblocking=[r for r in requirements if not r["blocking"]]
 def sv(r):return 1.0 if r["status"]=="PASS" else (.5 if r["status"]=="PARTIAL" else 0.0)
 readiness=100*(sum(sv(r) for r in blocking)+.35*sum(sv(r) for r in nonblocking))/max(1,len(blocking)+.35*len(nonblocking))
 er=sum(max(0,r["required_evidence"]) for r in requirements); ep=sum(min(r["evidence_count"],r["required_evidence"]) for r in requirements); evidence=100 if er==0 else 100*ep/er
 sr=shipment.get("supplier_required",0) or 0; sc=shipment.get("supplier_complete",0) or 0; supplier=100 if sr==0 else min(100,100*sc/sr)
 ready=all(r["status"]=="PASS" for r in blocking)
 return {"auto_ready":ready,"readiness_score":round(readiness,1),"evidence_completeness_pct":round(evidence,1),"supplier_data_coverage_pct":round(supplier,1),"blockers":[r["label"] for r in blocking if r["status"]!="PASS"]}
def portfolio_metrics(scored):
 total=sum(s["value_eur"] for s in scored); ready=sum(s["value_eur"] for s in scored if s["score"]["auto_ready"])
 def vw(k):return 0.0 if total==0 else sum(s["value_eur"]*s["score"][k] for s in scored)/total
 cycles=[s["verification_cycle_days"] for s in scored if s.get("verification_cycle_days") is not None]
 return {"eu_bound_value_eur":round(total,2),"auto_compliance_ready_value_eur":round(ready,2),"auto_compliance_ready_value_pct":round(100*ready/total,1) if total else 0,"evidence_completeness_pct":round(vw("evidence_completeness_pct"),1),"supplier_data_coverage_pct":round(vw("supplier_data_coverage_pct"),1),"verification_cycle_days_median":round(median(cycles),1) if cycles else None,"manual_compliance_hours_per_shipment":round(sum(s["manual_hours"] for s in scored)/len(scored),1) if scored else 0,"shipments":len(scored),"ready_shipments":sum(1 for s in scored if s["score"]["auto_ready"])}
