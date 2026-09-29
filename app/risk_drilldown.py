from __future__ import annotations
from collections import defaultdict
from .db import connect,rows
def _risk_row(shipment,req,links,requests):
 supplier_rows=[]
 for link in links:
  if link["shipment_id"]!=shipment["id"]:continue
  supplier_rows.append({"supplier_id":link["supplier_id"],"supplier_name":link["supplier_name"],"material":link["material"],"required_evidence_type":link["required_evidence_type"],"request_id":link.get("request_id"),"request_status":link.get("request_status"),"owner":link.get("owner"),"due_date":link.get("due_date")})
 return {"shipment_id":shipment["id"],"shipment_no":shipment["shipment_no"],"country":shipment["destination_country"],"product":shipment["product"],"value_eur":shipment["value_eur"],"blocker":{"code":req["code"],"label":req["label"],"status":req["status"],"notes":req["notes"]},"suppliers":supplier_rows}
def risk_drilldown():
 with connect() as conn:
  shipments=rows(conn,"SELECT * FROM shipments WHERE value_eur>0 ORDER BY value_eur DESC")
  reqs=rows(conn,"SELECT * FROM requirements WHERE blocking=1 AND status!='PASS'")
  links=rows(conn,"""SELECT l.*,s.name supplier_name,r.id request_id,r.status request_status,r.owner,r.due_date
   FROM supplier_shipment_links l JOIN suppliers s ON s.id=l.supplier_id
   LEFT JOIN evidence_requests r ON r.shipment_id=l.shipment_id AND r.supplier_id=l.supplier_id AND r.status='OPEN'""")
 by_shipment=defaultdict(list)
 for r in reqs:by_shipment[r["shipment_id"]].append(r)
 countries=defaultdict(lambda:{"total_value_eur":0.0,"at_risk_value_eur":0.0,"shipments":[]})
 rule_risk=defaultdict(float); at_risk_shipments=set(); drill=[]
 for s in shipments:
  countries[s["destination_country"]]["total_value_eur"]+=s["value_eur"]
  blockers=by_shipment.get(s["id"],[])
  if blockers:
   at_risk_shipments.add(s["id"]); countries[s["destination_country"]]["at_risk_value_eur"]+=s["value_eur"]
   for r in blockers:
    rule_risk[r["code"]]+=s["value_eur"]; drill.append(_risk_row(s,r,links,[]))
   countries[s["destination_country"]]["shipments"].append({"shipment_id":s["id"],"shipment_no":s["shipment_no"],"value_eur":s["value_eur"],"blocker_count":len(blockers)})
 total=sum(s["value_eur"] for s in shipments); risk=sum(s["value_eur"] for s in shipments if s["id"] in at_risk_shipments)
 return {"data_status":"CONNECTED_SHIPMENT_DATA","metrics":{"eu_order_book_eur":total,"market_ready_value_eur":total-risk,"revenue_at_risk_eur":risk,"market_ready_value_pct":round(100*(total-risk)/total,1) if total else 0},"countries":[{"country":k,**v} for k,v in sorted(countries.items(),key=lambda x:x[1]["at_risk_value_eur"],reverse=True)],"rule_risk":[{"code":k,"value_eur":v} for k,v in sorted(rule_risk.items(),key=lambda x:x[1],reverse=True)],"drilldown":drill}
