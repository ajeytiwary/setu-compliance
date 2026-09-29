import json
from pathlib import Path
import pytest
from app import data_sources as ds
from app.source_adapters import adapter_for
def test_registry_has_rich_demo_sources():
 r=ds.registry()
 required={"taric_measures","quota_balances","eucdm","steel_2026_1457","cbam_defaults","cbam_benchmarks","echa_candidate_list","scip_schema","eu_sanctions","comext_trade","industrial_telemetry_demo"}
 assert required <= set(r)
def test_authority_and_demo_are_distinct():
 assert ds.selected("steel_2026_1457").legal_authority is True
 assert ds.selected("industrial_telemetry_demo").authority=="DEMO_ONLY"
def test_provider_is_swappable(tmp_path,monkeypatch):
 cfg={"schema_version":1,"datasets":{"x":{"purpose":"x","authority_required":False,"refresh":"manual","providers":[{"id":"a","kind":"json","authority":"OFFICIAL","legal_authority":False,"url":"https://a","enabled":False},{"id":"b","kind":"json","authority":"MIRROR","legal_authority":False,"url":"https://b","enabled":True}]}}}
 p=tmp_path/"sources.json";p.write_text(json.dumps(cfg));monkeypatch.setattr(ds,"CONFIG",p)
 assert ds.selected("x").id=="b"
def test_landing_page_never_becomes_snapshot_truth():
 p=ds.selected("echa_candidate_list")
 result=adapter_for(p).fetch(p)
 assert result["status"]=="DISCOVERY_REQUIRED"
