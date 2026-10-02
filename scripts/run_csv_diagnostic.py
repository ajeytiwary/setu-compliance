#!/usr/bin/env python3
"""Zero-integration shipment diagnostic.

Reads a shipment CSV plus optional evidence JSON. It never treats missing data as
READY. Output is a diagnostic triage result, not customs/CBAM authority acceptance.
Optional --outcomes CSV adds observed acceptance labels and computes false-ready /
false-block rates for post-pilot validation.
"""
from __future__ import annotations
import argparse,csv,json
from pathlib import Path

REQUIRED=("transaction_id","po_number","cn_code","origin","destination","shipment_date","quantity_t","line_value_eur")
REQUIRED_EVIDENCE=("COMMERCIAL_INVOICE","CBAM_INSTALLATION_DATA","ORIGIN_DECLARATION","TARIC_SUPPORTING_DOCUMENT")
BAD={"STALE","EXPIRED","UNVERIFIED","CONFLICTING","MISSING","SUPERSEDED"}

def load_csv(path):
 with open(path,newline="",encoding="utf-8-sig") as f:return list(csv.DictReader(f))

def diagnose(rows,evidence):
 by_tx={}
 for e in evidence:
  by_tx.setdefault(e.get("transaction_id"),[]).append(e)
 results=[]
 for r in rows:
  missing=[k for k in REQUIRED if not str(r.get(k) or "").strip()]
  ev=by_tx.get(r.get("transaction_id"),[])
  by_type={e.get("type"):e for e in ev}
  blockers=[]
  for typ in REQUIRED_EVIDENCE:
   item=by_type.get(typ)
   if not item:blockers.append({"code":"EVIDENCE_MISSING","evidence_type":typ})
   elif str(item.get("status","")).upper() in BAD:blockers.append({"code":"EVIDENCE_"+str(item.get("status")).upper(),"evidence_type":typ})
  for k in missing:blockers.append({"code":"FIELD_MISSING","field":k})
  try:value=float(r.get("line_value_eur") or 0)
  except ValueError:value=0.0;blockers.append({"code":"FIELD_INVALID","field":"line_value_eur"})
  results.append({"transaction_id":r.get("transaction_id"),"po_number":r.get("po_number"),
                  "status":"BLOCKED" if blockers else "READY_FOR_DIAGNOSTIC_REVIEW",
                  "line_value_eur":value,"blockers":blockers})
 return results

def metrics(results,outcomes=None):
 total=sum(x["line_value_eur"] for x in results)
 blocked=[x for x in results if x["status"]=="BLOCKED"]
 out={"transactions":len(results),"order_book_eur":round(total,2),"blocked":len(blocked),
      "blocked_value_eur":round(sum(x["line_value_eur"] for x in blocked),2),
      "ready_for_diagnostic_review":len(results)-len(blocked)}
 if outcomes is not None:
  truth={r["transaction_id"]:str(r.get("accepted") or "").strip().lower() in {"1","true","yes","accepted"} for r in outcomes}
  scored=[x for x in results if x["transaction_id"] in truth]
  fr=sum(1 for x in scored if x["status"]!="BLOCKED" and not truth[x["transaction_id"]])
  fb=sum(1 for x in scored if x["status"]=="BLOCKED" and truth[x["transaction_id"]])
  out.update({"outcomes_scored":len(scored),"false_ready":fr,"false_block":fb,
              "false_ready_rate":fr/len(scored) if scored else None,
              "false_block_rate":fb/len(scored) if scored else None})
 return out

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("transactions_csv");ap.add_argument("--evidence-json")
 ap.add_argument("--outcomes");ap.add_argument("--output",default="diagnostic-report.json")
 a=ap.parse_args()
 rows=load_csv(a.transactions_csv)
 evidence=json.loads(Path(a.evidence_json).read_text()) if a.evidence_json else []
 outcomes=load_csv(a.outcomes) if a.outcomes else None
 results=diagnose(rows,evidence);report={"scope":"ZERO_INTEGRATION_DIAGNOSTIC","metrics":metrics(results,outcomes),"results":results,
 "guardrail":"READY_FOR_DIAGNOSTIC_REVIEW is triage only; it is not customs acceptance, CBAM Registry acceptance, verifier acceptance or legal certification."}
 Path(a.output).write_text(json.dumps(report,indent=2)+"\n")
 print(json.dumps(report["metrics"],indent=2))
if __name__=="__main__":main()
