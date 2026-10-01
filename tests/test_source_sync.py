import io,zipfile
from app.source_sync import normalize_candidate_csv,normalize_sanctions,normalize_scip,validate
def z(files):
 b=io.BytesIO()
 with zipfile.ZipFile(b,"w") as f:
  for n,c in files.items():f.writestr(n,c)
 return b.getvalue()
def test_candidate_csv_normalization():
 r=normalize_candidate_csv(b"Substance name,EC number,CAS number,Reason for inclusion\nLead,231-100-4,7439-92-1,Toxic\n")
 assert r[0]["ec_number"]=="231-100-4"
def test_sanctions_csv_normalization():
 r=normalize_sanctions(b"EU reference number,Name,Programme\nEU.1,Example,TEST\n","csv")
 assert r[0]["eu_reference"]=="EU.1"
def test_scip_zip_inventory():
 r=normalize_scip(z({"picklists/a.xml":"<x/>","validation/rules.xml":"<x/>","schema/a.xsd":"x"}))
 assert r[0]["version"]=="6.10" and r[0]["schema_files"]
def test_validation_fails_closed():
 assert not validate("echa_candidate_list",[{"x":1}])["valid"]
 assert not validate("taric_measures",[])["valid"]


def test_eucdm_upstream_failure_returns_explicit_stale_fallback(tmp_path,monkeypatch):
 import json
 import app.source_sync as ss
 root=tmp_path/"normalized"; latest=root/"eucdm"/"latest.json";latest.parent.mkdir(parents=True)
 latest.write_text(json.dumps({"dataset":"eucdm","sha256":"validated-sha","validation":{"valid":True},"transport":"PRIMARY"}))
 monkeypatch.setattr(ss,"NORMALIZED",root)
 monkeypatch.setattr(ss,"get",lambda *a,**k: (_ for _ in ()).throw(Exception("HTTP 403")))
 out=ss.sync("eucdm")
 assert out["sha256"]=="validated-sha"
 assert out["transport"]=="STALE_VALIDATED_FALLBACK"
 assert "Fresh EUCDM fetch failed" in out["sync_warning"]
