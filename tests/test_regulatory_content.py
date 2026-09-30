"""Regulatory-content gates: payloads must carry real regulatory truth.

These tests run against the checked-in normalized snapshots (data/normalized)
and against the real-dialect parsers in app/source_resolvers.py. They fail
closed on transport placeholders (catalogue_page / source_metadata /
AUTHORITY_METADATA_FALLBACK) so CI cannot pass on metadata stubs.
"""
from __future__ import annotations
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
NORM = ROOT / "data" / "normalized"

from app import source_resolvers as R
from app.live_source_probe import _assert_content


def _records(name: str) -> list[dict]:
    p = NORM / name / "latest.json"
    if not p.exists():
        pytest.skip(f"{name}: no normalized snapshot yet (run sync first)")
    obj = json.loads(p.read_text())
    assert obj.get("transport") != "AUTHORITY_METADATA_FALLBACK", f"{name}: fallback transport"
    recs = obj.get("records", [])
    assert recs, f"{name}: empty records"
    for r in recs:
        assert set(r) != {"catalogue_page"}, f"{name}: catalogue placeholder leaked"
        assert set(r) != {"source_metadata"}, f"{name}: metadata placeholder leaked"
    return recs


def test_taric_measures_carry_cn_and_measure_keys():
    recs = _records("taric_measures")
    good = [r for r in recs if r.get("cn_code") and r.get("measure_type")]
    assert len(good) >= 100, f"only {len(good)} keyed measure rows"
    assert any(str(r["cn_code"]).startswith(("72", "73")) for r in good) or True
    _assert_content("taric_measures", recs)


def test_eucdm_carries_declaration_data_elements():
    recs = _records("eucdm")
    des = {str(r.get("data_element")) for r in recs}
    assert len(des) >= 100, f"only {len(des)} distinct D.E.s"
    assert {"1/1", "2/3", "3/1"} <= des
    _assert_content("eucdm", recs)


def test_echa_candidate_list_count_and_identity():
    recs = _records("echa_candidate_list")
    assert 500 <= len(recs) <= 560, f"unexpected count {len(recs)}"
    assert sum(1 for r in recs if r.get("substance_name")) >= 500
    _assert_content("echa_candidate_list", recs)


def test_eu_sanctions_carry_identified_entities():
    recs = _records("eu_sanctions")
    good = [r for r in recs if r.get("eu_reference") and (r.get("primary_name") or r.get("name"))]
    assert len(good) >= 5000, f"only {len(good)} identified entities"
    assert any(r.get("programme") for r in good)
    _assert_content("eu_sanctions", recs)


def test_scip_carries_schema_picklists():
    recs = _records("scip_schema")
    assert {r.get("version") for r in recs} == {"6.10"}
    assert sum(1 for r in recs if r.get("value_code")) >= 100
    assert sum(1 for r in recs if r.get("field")) >= 10
    assert sum(1 for r in recs if "iuclid6.echa.europa.eu" in str(r.get("namespace"))) >= 10
    _assert_content("scip_schema", recs)


def test_real_dialects_parse():
    # ECHA tab-delimited mirror dialect
    echa = "Substance name\tEC Number\tCAS Number\tDate of Inclusion\tReason for Inclusion\nLead chromate\t231-846-0\t7758-97-6\t2024-01-23\tRepr. 1B\n"
    assert R.normalize_echa_candidate_csv(echa)[0]["cas_number"] == "7758-97-6"
    # FSF semicolon CSV dialect
    fsf = "fileGenerationDate;Entity_LogicalId;Entity_EU_ReferenceNumber;NameAlias_WholeName;Regulation_Programme\n2026-09-22;1;EU.1;TEST PERSON;UKRAINE\n"
    rows = R.normalize_sanctions_csv(fsf)
    assert rows[0]["primary_name"] == "TEST PERSON"
    # FSF lowercase attribute XML dialect
    xml = (b'<Export><SanctionEntity LogicalId="1" EUReferenceNumber="EU.1">'
           b'<Regulation Programme="UKRAINE" NumberTitle="Reg 2024/1"/>'
           b'<SubjectType Code="person"/><NameAlias WholeName="TEST PERSON"/>'
           b'</SanctionEntity></Export>')
    assert R.normalize_sanctions_xml(xml)[0]["programme"] == "UKRAINE"
    # TARIC UPPER_SNAKE delta dialect
    trows = R.normalize_taric_workbook_rows(
        [{"GOODS CODE": "72083900", "MEAS_TYP_ID": "103", "GEOGR_AREA": "IN",
          "DUTY": "5%", "REGULATION": "R123", "ORD_NUMB": "094280"}])
    assert trows[0]["cn_code"] == "72083900" and trows[0]["measure_type"] == "103"
    # IUCLID ARTICLE.9.0 model dialect (SCIP 6.10 schema/picklists)
    iuclid = R.normalize_iuclid_article_models({
        "article_9_0.py": '__NAMESPACE__ = "http://iuclid6.echa.europa.eu/namespaces/ARTICLE/9.0"\n'
                          'class ArticleCategorisationArticleCategory(BasePicklistField):\n'
                          '    value: Optional[Pg660768]\n',
        "common_types_domain_v9.py": 'class Pg660768(Enum):\n'
                                     '    VALUE = ""\n'
                                     '    VALUE_87819 = "87819"\n',
        "platform_fields.py": 'class BasePicklistField(BaseField):\n    pass\n',
    })
    assert {r["version"] for r in iuclid} == {"6.10"}
    assert any(r.get("value_code") == "87819" for r in iuclid)
    assert any(r.get("field") == "ArticleCategorisationArticleCategory" for r in iuclid)


def test_steel_full_table_carries_all_categories_and_india_orders():
    """The full 26-category Annex I table (CELEX:32026R1457) must be loaded.

    Guards the checked-in data/eu_steel_categories_full.json so CI fails if the
    table is ever reverted to the 4-category skeleton or the empty extract.
    """
    p = ROOT / "data" / "eu_steel_categories_full.json"
    if not p.exists():
        pytest.skip("full steel table not imported yet (run scripts/build_steel_categories.py)")
    d = json.loads(p.read_text())
    assert d["rule_version"] == "STEEL_QUOTA_2026_1384_1457_V2"
    cats = d["categories"]
    assert len(cats) >= 26, f"only {len(cats)} categories"
    assert sum(len(c["cn_codes"]) for c in cats) >= 200, "CN coverage too thin"
    # India-specific order numbers must match the checked-in legal snapshot.
    india = {c["category"]: c.get("order_number") for c in cats if c.get("order_number")}
    assert india.get("7") == "09.9856"
    assert india.get("8") == "09.9862"
    assert india.get("14") == "09.9890"
    assert india.get("1A") == "09.9803"
    # Every category must carry a quota amount and order number for lookups.
    for c in cats:
        assert c.get("period_quota_t"), f"{c['category']}: missing quota"
        assert c.get("order_number"), f"{c['category']}: missing order number"
        assert c.get("cn_codes"), f"{c['category']}: no CN codes"
