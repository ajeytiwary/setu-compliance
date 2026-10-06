from pathlib import Path

from app.content_pages import api_workflow_run_parse
from app.pdf_image_ocr import extract_image_ocr

BASE = Path(__file__).resolve().parents[1] / "data" / "client_data"


def test_image_only_mtc_uses_review_only_ocr_without_false_cn():
    path=BASE / "scribd-903558901.pdf"
    document=api_workflow_run_parse([(path.name,path.read_bytes())])["documents"][0]
    assert document["ok"]
    assert document["selected_parser"]=="tesseract-image-ocr"
    assert document["ocr_review"]["ok"]
    assert document["ocr_review"]["pages"][0]["lines"]
    assert document["extracted"]["cn_codes_found"]==[]
    assert document["candidates"]==[]


def test_invoice_ocr_keeps_item_row_box_for_review():
    path=BASE / "scribd-975352350.pdf"
    result=extract_image_ocr(path.read_bytes(),path.name)
    assert result["ok"] and result["review_status"]=="REQUIRES_REVIEW"
    line=next(x for x in result["pages"][0]["lines"] if "73071120" in x["text"])
    assert "214" in line["text"] and "17,360.77" in line["text"]
    assert "30,670.32" in line["text"] and len(line["bbox"])==4
    assert all(word["bbox"] for word in result["pages"][0]["words"])
