import asyncio
import json

import httpx
from fastapi.testclient import TestClient

from app.llm_document_ingest import propose_pdf_lines, validate_proposal


PAGES = [["Invoice INV-77 origin IN destination NL date 2026-10-03",
          "CN 72085120 QTY 2 MT VALUE EUR 1000"]]
ROW = PAGES[0][1]


def ref(raw, line, quote):
    return {"raw": raw, "page": 1, "line": line, "quote": quote}


def proposal():
    return {"lines": [{"fields": {
        "invoice_number": ref("INV-77", 1, PAGES[0][0]),
        "cn_code": ref("72085120", 2, ROW),
        "quantity": ref("2", 2, ROW),
        "quantity_unit": ref("MT", 2, ROW),
        "value": ref("1000", 2, ROW),
        "currency": ref("EUR", 2, ROW),
        "origin_country": ref("IN", 1, PAGES[0][0]),
        "destination_country": ref("NL", 1, PAGES[0][0]),
        "import_date": ref("2026-10-03", 1, PAGES[0][0]),
    }}]}


def test_exact_citations_become_review_candidates():
    out = validate_proposal(proposal(), PAGES, "invoice.pdf", "a" * 64, "model/test")
    line = out["lines"][0]
    assert line["cn_code"] == "72085120"
    assert line["quantity_t"] == 2
    assert line["field_provenance"]["cn_code"]["page"] == 1
    assert line["field_provenance"]["cn_code"]["line"] == 2
    assert "PDF_BOUNDING_BOX_UNAVAILABLE" in line["issues"]


def test_fabricated_value_is_rejected():
    bad = proposal()
    bad["lines"][0]["fields"]["value"]["raw"] = "999999"
    out = validate_proposal(bad, PAGES, "invoice.pdf", "a" * 64, "model/test")
    line = out["lines"][0]
    assert line["customs_value_eur"] is None
    assert "LLM_CITATION_REJECTED:value" in line["issues"]


def test_cross_row_values_are_rejected():
    pages = [PAGES[0] + ["filler"] * 10 + ["VALUE EUR 1000"]]
    bad = proposal()
    bad["lines"][0]["fields"]["value"] = ref("1000", 13, pages[0][12])
    out = validate_proposal(bad, pages, "invoice.pdf", "a" * 64, "model/test")
    line = out["lines"][0]
    assert "LLM_ROW_ASSOCIATION_REJECTED" in line["issues"]
    assert line["cn_code"] is None


def test_gateway_request_uses_configured_model_and_never_returns_secret(monkeypatch):
    from app import llm_document_ingest as llm
    monkeypatch.setattr(llm, "_source_pages", lambda data: PAGES)
    monkeypatch.setenv("EUROSETU_INGEST_LLM_API_KEY", "test-secret")
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"data": {"choices": [{"message": {"content": json.dumps(proposal())}}]}})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        out = asyncio.run(propose_pdf_lines(b"pdf", "invoice.pdf", "model/test", client))
    finally:
        asyncio.run(client.aclose())
    assert seen["url"].endswith("/api/v1/chat/completions")
    assert seen["body"]["model"] == "model/test"
    assert seen["auth"] == "Bearer test-secret"
    assert "test-secret" not in json.dumps(out)
    assert out["ok"]


def test_public_parse_cannot_trigger_model_call_without_pilot_token():
    from app.main import app
    response = TestClient(app).post("/api/workflow-run/parse", data={"use_llm": "true"})
    assert response.status_code in (401, 403)


def test_website_exposes_model_control_without_secret(monkeypatch):
    from app.main import app
    monkeypatch.setenv("EUROSETU_INGEST_LLM_API_KEY", "test-secret")
    client = TestClient(app)
    page = client.get("/workflow-run")
    assert page.status_code == 200
    assert 'id="model-id"' in page.text
    assert 'id="use-llm"' in page.text
    config = client.get("/api/workflow-run/model-config")
    assert config.status_code == 200
    assert config.json()["default_model"] == "deepseek/deepseek-v4-flash"
    assert "test-secret" not in page.text + config.text
