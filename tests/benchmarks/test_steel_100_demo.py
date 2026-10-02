"""STEEL-100-DEMO: public synthetic steel portfolio with broken evidence chains.

100 EU-bound steel transactions. Twenty-five begin BLOCKED because of a
deterministic evidence defect. Remediation creates a successor decision with
new evidence provenance and moves every affected transaction to READY while
preserving the predecessor decision hash.
"""
from __future__ import annotations
import hashlib, json, random
from app.benchmark_harness import BenchmarkCase
from app.decision_engine import build_decision

AS_OF="2026-09-29"
SOURCE={"id":"DEMO-RULESET-2026-09-29","version":"2026.09.29",
        "sha256":hashlib.sha256(b"eurosetu-demo-ruleset-2026-09-29").hexdigest()}
FAULTS=["MISSING_INSTALLATION","MISSING_PRECURSOR","STALE_SUPPLIER_EVIDENCE",
        "UNVERIFIED_EMISSIONS","MISSING_TARIC_DOCUMENT"]

def ob(oid,status,reason="",evidence=None):
    return {"obligation_id":oid,"applicable":True,"status":status,
            "reasons":[reason] if reason else [],"severity":"BLOCKING",
            "required_for_release":True,"evidence_refs":evidence or [],
            "rule_refs":[SOURCE["id"]],"schema_version":"EUROSETU_CANONICAL_V1"}

def portfolio():
    rng=random.Random(20261002); out=[]
    cns=["72083900","72085120","72107080","72191390","72254060"]
    destinations=["NL","DE","BE","FR","IT"]
    for i in range(100):
        fault=FAULTS[i%len(FAULTS)] if i<25 else None
        out.append({"transaction_ref":f"STEEL100-{i+1:03d}",
                    "order_id":f"EU-PO-{1000+i}","cn_code":cns[i%len(cns)],
                    "origin_country":"IN","destination_country":destinations[i%5],
                    "line_value":round(rng.uniform(25000,220000),2),
                    "fault":fault})
    return out

def before_after(tx):
    base=[ob("CBAM_APPLICABILITY","PASS",evidence=["CN-2026"]),
          ob("TARIC_APPLICABILITY","PASS",evidence=["TARIC-SNAPSHOT"]),
          ob("ORIGIN","PASS",evidence=["ORIGIN-DECL"])]
    if not tx["fault"]:
        before=build_decision(tx["transaction_ref"],base+[ob("EVIDENCE_CHAIN","PASS",evidence=["EV-VALID"])],
                              as_of=AS_OF,source_snapshot_refs=[SOURCE],
                              evidence_snapshot_refs=["EV-VALID"])
        return before,before
    before=build_decision(tx["transaction_ref"],base+[ob("EVIDENCE_CHAIN","MISSING",tx["fault"])],
                          as_of=AS_OF,source_snapshot_refs=[SOURCE],
                          evidence_snapshot_refs=[])
    ev=f"EV-REMEDIATED-{tx['transaction_ref']}"
    after=build_decision(tx["transaction_ref"],base+[ob("EVIDENCE_CHAIN","PASS","remediated",[ev])],
                         as_of=AS_OF,source_snapshot_refs=[SOURCE],
                         evidence_snapshot_refs=[ev],predecessor_id=before["decision_id"])
    return before,after

def test_steel_100_blocked_remediation_ready_with_provenance():
    case=BenchmarkCase("STEEL-100-DEMO","portfolio_100_001","SYNTHETIC",AS_OF)
    txs=portfolio(); pairs=[before_after(t) for t in txs]
    before=[p[0] for p in pairs]; after=[p[1] for p in pairs]
    blocked=[d for d in before if d["status"]=="BLOCKED"]
    remediated=[(b,a) for b,a in pairs if b["status"]=="BLOCKED"]
    total_value=round(sum(t["line_value"] for t in txs),2)
    blocked_value=round(sum(t["line_value"] for t,d in zip(txs,before) if d["status"]=="BLOCKED"),2)
    case.assert_and_emit({
        "transactions":len(txs),"blocked_before":len(blocked),
        "ready_before":sum(d["status"]=="READY" for d in before),
        "ready_after":sum(d["status"]=="READY" for d in after),
        "remediated_to_ready":sum(a["status"]=="READY" for _,a in remediated),
        "predecessors_preserved":all(a["predecessor_id"]==b["decision_id"] for b,a in remediated),
        "source_provenance":all(d["source_snapshot_refs"]==[SOURCE] for d in after),
        "evidence_provenance":all(bool(a["evidence_snapshot_refs"]) for _,a in remediated),
        "decision_hash_changed":all(a["decision_hash"]!=b["decision_hash"] for b,a in remediated),
        "total_value_positive":total_value>0,"blocked_value_positive":blocked_value>0,
        "fault_types":len({t["fault"] for t in txs if t["fault"]})
    },{
        "transactions":100,"blocked_before":25,"ready_before":75,"ready_after":100,
        "remediated_to_ready":25,"predecessors_preserved":True,
        "source_provenance":True,"evidence_provenance":True,
        "decision_hash_changed":True,"total_value_positive":True,
        "blocked_value_positive":True,"fault_types":5
    },source_snapshots=[SOURCE],
      extra={"demo":{"synthetic":True,"total_value_eur":total_value,
                    "blocked_value_before_eur":blocked_value,
                    "faults":FAULTS,
                    "flow":"BLOCKED -> evidence remediation -> READY"}})
