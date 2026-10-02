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
 assert {"ec_cbam_examples","ec_cbam_defaults","ec_cbam_benchmarks","ec_cbam_operator_guidance","uci_steel_energy","docile","carbonchain_steelforce","carbonchain_spaeter","eurostat_comext","taric","un_comtrade","worldsteel_lci","voestalpine_epds","cord_receipts","quest_tables","cbamreturn_worked_example","terlouw_steel_cbam"}<=ids
 assert all(x["source_class"] and x["license"] and x["url"] for x in cfg["sources"])
def test_evidence_room_2026_layout_and_expected():
 subprocess.run([sys.executable,"scripts/build_public_evidence_corpus.py","--clean"],cwd=ROOT,check=True)
 subprocess.run([sys.executable,"scripts/build_evidence_room_2026.py","--clean"],cwd=ROOT,check=True)
 room=ROOT/"data/public_trade_evidence/EU-STEEL-EXPORT-2026"
 for sub in ["ERP","LOGISTICS/invoices","LOGISTICS/packing_lists","LOGISTICS/customs_declarations","QUALITY/mill_test_certificates","CARBON/cbam_supplier_templates","CARBON/epds","CARBON/verification","REGULATORY/taric","REGULATORY/cbam","REGULATORY/sanctions","expected"]:
  assert (room/sub).exists(), sub
 init=json.loads((room/"expected/initial_decisions.json").read_text())
 assert (init["READY"],init["BLOCKED"])==(75,25)
 prov=json.loads((room/"provenance.json").read_text())
 assert prov["layers"]==["regulatory-goldens","public-real-world","competitor-scenarios","synthetic-corrupted"]
 assert all(a["sha256"] and len(a["sha256"])==64 for a in prov["artifacts"])
 der=json.loads((room/"corrupted_derivatives.json").read_text())
 assert len(der)==25 and all(d["parent_artifact_sha256"] for d in der)
 assert {d["chaos_id"] for d in der}<={f"CHAOS-{i:03d}" for i in range(1,16)}
