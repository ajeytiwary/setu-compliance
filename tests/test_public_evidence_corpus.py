import csv,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_public_evidence_corpus_builds_offline_and_is_deterministic():
 subprocess.run([sys.executable,"scripts/build_public_evidence_corpus.py","--clean"],cwd=ROOT,check=True)
 base=ROOT/"data/public_trade_evidence"; m=json.loads((base/"manifest.json").read_text())
 with (base/"evidence_room/transactions.csv").open() as f: tx=list(csv.DictReader(f))
 ev=json.loads((base/"evidence_room/evidence.json").read_text()); truth=json.loads((base/"evidence_room/fault_truth.json").read_text())
 assert len(tx)==100 and len({x["transaction_id"] for x in tx})==100
 assert sum(bool(x["injected_fault"]) for x in tx)==25
 assert truth["expected_initial"]=={"READY":75,"BLOCKED":25}
 assert truth["expected_after_remediation"]=={"READY":100,"BLOCKED":0}
 assert all(a["source_class"]=="SYNTHETIC" for a in m["artifacts"])
 assert all(a["sha256"] and len(a["sha256"])==64 for a in m["artifacts"])
 assert len(ev)>500
def test_source_registry_has_required_provenance():
 cfg=json.loads((ROOT/"config/public_evidence_sources.json").read_text())
 ids={x["id"] for x in cfg["sources"]}
 assert {"ec_cbam_examples","ec_cbam_defaults","ec_cbam_benchmarks","uci_steel_energy","docile","carbonchain_steelforce","carbonchain_spaeter","eurostat_comext","taric"}<=ids
 assert all(x["source_class"] and x["license"] and x["url"] for x in cfg["sources"])
