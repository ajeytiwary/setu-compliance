from pathlib import Path

from app.pdf_observations import extract_pdf_observations, invoice_candidates, reconcile_documents

BASE = Path(__file__).resolve().parents[1] / "data" / "client_data"


def obs(doc_id):
    path = BASE / f"scribd-{doc_id}.pdf"
    return extract_pdf_observations(path.read_bytes(), path.name)


def test_public_invoice_row_is_source_addressable_and_review_only():
    o = obs("975352350")
    assert o["status"] == "REQUIRES_REVIEW"
    assert [(t["kind"], len(t["rows"])) for t in o["tables"]] == [("invoice_items", 1)]
    row = o["tables"][0]["rows"][0]
    assert (row["hs_code"], row["pieces"], row["net_weight_kg_raw"], row["value_raw"]) == (
        "73071120", 214, "17,360.77", "30,670.32")
    assert row["source"]["page"] == 1 and row["source"]["bbox"]
    candidates = invoice_candidates(o)
    assert len(candidates) == 1
    assert candidates[0]["review_status"] == "REQUIRES_REVIEW"
    assert candidates[0]["customs_value_eur"] is None
    assert "EUR_CONVERSION_REQUIRES_RATE_SNAPSHOT" in candidates[0]["issues"]
    assert "ICIC0002394" not in {f["raw"] for f in o["fields"] if f["field"] == "container_number"}


def test_packing_rows_and_negative_linkage():
    o = obs("800499484")
    assert sum(len(t["rows"]) for t in o["tables"] if t["kind"] == "packing_items") == 25
    assert not any(f["field"] == "hs_code" for f in o["fields"])
    docs = [{"observations": obs(i)} for i in
            ("975352350", "975352347", "975352352", "800499484", "800499503", "574284615")]
    graph = reconcile_documents(docs)
    assert len(graph["edges"]) == 4
    assert {tuple(e[k] for k in ("from", "to")) for e in graph["edges"]} == {
        (0, 1), (0, 2), (1, 2), (3, 4)}
    assert len(graph["conflicts"]) == 2
    assert all(c["field"] == "net_weight_kg" for c in graph["conflicts"])
    assert all(c["documents"][1] == 2 for c in graph["conflicts"])
    assert not any(5 in (e["from"], e["to"]) for e in graph["edges"])
