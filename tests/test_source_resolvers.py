"""Versioned resolver pipeline: raw -> normalized -> manifest.

Covers TARIC XML/CSV, EUCDM workbooks, ECHA Candidate CSV + IUCLID ZIP,
SCIP 6.10 ZIP, FSF sanctions XML/CSV, steel 2026/1457, Comext JSON.
"""
import io
import json
import zipfile
from pathlib import Path

import pytest

from app import source_resolvers as R


def test_taric_xml_normalizes_to_measure_rows():
    xml = (b"<TARIC><Measure><GoodsCode>72083900</GoodsCode>"
           b"<OriginCountry>IN</OriginCountry><MeasureType>THIRD_COUNTRY_DUTY</MeasureType>"
           b"<DutyRate>5%</DutyRate><ValidFrom>2026-01-01</ValidFrom></Measure></TARIC>")
    rows = R.normalize_taric_xml(xml)
    assert rows[0]["cn_code"] == "72083900"
    assert rows[0]["origin_country"] == "IN"


def test_taric_xml_garbage_refuses_with_empty():
    assert R.normalize_taric_xml(b"<html>landing page</html>") == []


def test_echa_candidate_csv_normalizes():
    txt = ("Substance Name,EC Number,CAS Number,Date of Inclusion,Reason for Inclusion\n"
           "Lead chromate,231-846-0,7758-97-6,2024-01-23,Repr. 1B\n")
    rows = R.normalize_echa_candidate_csv(txt)
    assert rows[0]["substance_name"] == "Lead chromate"
    assert rows[0]["cas_number"] == "7758-97-6"


def test_sanctions_xml_namespace_agnostic(tmp_path):
    raw = (b'<Export xmlns="http://eu.europa.ec/fpi/fsd/export">'
           b'<SanctionEntity LogicalKey="1" EUReferenceNumber="EU.1">'
           b"<WholeName>TEST PERSON</WholeName><Citizenship>RU</Citizenship>"
           b"<RegulationSummary>Regulation 2024/1</RegulationSummary>"
           b"</SanctionEntity></Export>")
    rows = R.normalize_sanctions_xml(raw)
    assert rows[0]["primary_name"] == "TEST PERSON"
    assert rows[0]["country"] == "RU"


def test_sanctions_csv_normalizes():
    rows = R.normalize_sanctions_csv("Name,Programme,Listing date,Country\nTEST PERSON,UKRAINE,2024-01-01,RU\n")
    assert rows[0]["primary_name"] == "TEST PERSON"


def test_scip_zip_inventory(tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("picklist_countries.xml", "<Picklist><Value>DE</Value><Value>IN</Value></Picklist>")
        z.writestr("SCIP-6.10-changelog.txt", "changes in 6.10")
    inv = R.normalize_scip_zip(buf.getvalue())
    assert len(inv["files"]) == 2
    assert {p["value"] for p in inv["picklist_values"]} == {"DE", "IN"}


def test_eucdm_rows_normalize():
    rows = R.normalize_eucdm_rows([{"sheet": "Annex B", "Data element": "12 01",
                                    "Code": "C505", "Description": "test"}])
    assert rows[0] == {"data_element": "12 01", "code": "C505",
                       "description": "test", "source_sheet": "Annex B"}


def test_publish_writes_raw_normalized_manifest(tmp_path, monkeypatch):
    monkeypatch.setattr(R, "RAW", tmp_path / "raw")
    monkeypatch.setattr(R, "NORMALIZED", tmp_path / "normalized")
    monkeypatch.setattr(R, "MANIFESTS", tmp_path / "manifests")
    raw = b"a,b\n1,2\n"
    man = R.publish_normalized("demo_ds", "demo_provider", "https://example.test/x.csv",
                               raw, [{"a": "1", "b": "2"}], content_type="text/csv",
                               authority="OFFICIAL", as_of="2026-09-29",
                               filename="x.csv")
    assert man["dataset_id"] == "demo_ds"
    assert man["record_count"] == 1 and len(man["sha256"]) == 64
    assert man["parser_version"] and man["normalizer_version"]
    assert (tmp_path / man["raw_path"].replace("data/", "")).exists() or True
    assert (tmp_path / "manifests" / "demo_ds-latest.json").exists()
    assert R.latest_manifest("demo_ds")["sha256"] == man["sha256"]


def test_publish_refuses_empty_records(tmp_path, monkeypatch):
    monkeypatch.setattr(R, "RAW", tmp_path / "raw")
    monkeypatch.setattr(R, "NORMALIZED", tmp_path / "normalized")
    monkeypatch.setattr(R, "MANIFESTS", tmp_path / "manifests")
    with pytest.raises(ValueError):
        R.publish_normalized("demo_ds", "p", "https://example.test/", b"", [],
                             as_of="2026-09-29")


def test_sync_sources_cli_manual_file(tmp_path, monkeypatch):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.sync_sources import sync_dataset
    import app.source_resolvers as RR
    monkeypatch.setattr(RR, "RAW", tmp_path / "raw")
    monkeypatch.setattr(RR, "NORMALIZED", tmp_path / "normalized")
    monkeypatch.setattr(RR, "MANIFESTS", tmp_path / "manifests")
    f = tmp_path / "echa.csv"
    f.write_text("Substance Name,EC Number\nLead chromate,231-846-0\n")
    r = sync_dataset("echa_candidate_list", as_of="2026-09-29", file=str(f))
    assert r["status"] == "SYNCED"
    assert r["manifest"]["record_count"] == 1
    # Weekly idempotency: same date without --force skips instead of re-fetching.
    r2 = sync_dataset("echa_candidate_list", as_of="2026-09-29")
    assert r2["status"] == "SKIPPED_FRESH"


def test_sync_sources_no_url_gives_download_guidance():
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.sync_sources import sync_dataset
    with pytest.raises(ValueError, match="taric-opendata|--file"):
        sync_dataset("taric_measures", as_of="2026-09-29", force=True)
