"""Bounded raster OCR for image-only PDFs and parser comparison.

Tesseract output is untrusted review material. Pixels are rendered at a fixed
DPI; word boxes are mapped back into PDF points. Nothing is auto-verified.
"""
from __future__ import annotations

import csv
import hashlib
import io
import shutil
import statistics
import subprocess
import tempfile
import time
from pathlib import Path

from pypdf import PdfReader

MAX_BYTES = 8 * 1024 * 1024
MAX_PAGES = 3
DPI = 170


def _group_words(words: list[dict]) -> list[dict]:
    groups: list[dict] = []
    for word in sorted(words, key=lambda w: ((w["pixel_bbox"][1]+w["pixel_bbox"][3])/2, w["pixel_bbox"][0])):
        center=(word["pixel_bbox"][1]+word["pixel_bbox"][3])/2
        group=min(groups,key=lambda g:abs(g["center"]-center),default=None)
        if group is None or abs(group["center"]-center)>10:
            group={"center":center,"words":[]};groups.append(group)
        group["words"].append(word)
        group["center"]=sum((w["pixel_bbox"][1]+w["pixel_bbox"][3])/2 for w in group["words"])/len(group["words"])
    lines=[]
    for group in sorted(groups,key=lambda g:g["center"]):
        ws=sorted(group["words"],key=lambda w:w["pixel_bbox"][0])
        boxes=[w["bbox"] for w in ws]
        lines.append({"text":" ".join(w["text"] for w in ws),
                      "bbox":[min(b[0] for b in boxes),min(b[1] for b in boxes),
                              max(b[2] for b in boxes),max(b[3] for b in boxes)],
                      "mean_confidence":round(statistics.mean(w["confidence"] for w in ws),1)})
    return lines


def extract_image_ocr(data:bytes,filename:str,max_pages:int=MAX_PAGES)->dict:
    started=time.perf_counter()
    digest=hashlib.sha256(data).hexdigest()
    base={"parser":"tesseract-image-ocr","filename":filename,"sha256":digest,
          "ok":False,"review_status":"REQUIRES_REVIEW","pages":[],"issues":[]}
    if len(data)>MAX_BYTES:return {**base,"code":"FILE_TOO_LARGE"}
    if not shutil.which("pdftoppm") or not shutil.which("tesseract"):
        return {**base,"code":"OCR_BINARY_UNAVAILABLE"}
    try:
        reader=PdfReader(io.BytesIO(data));total=len(reader.pages)
        if total>max_pages:return {**base,"code":"OCR_PAGE_LIMIT_EXCEEDED","page_count":total}
        with tempfile.TemporaryDirectory(prefix="eurosetu-ocr-") as temp:
            pdf=Path(temp)/"input.pdf";pdf.write_bytes(data)
            prefix=Path(temp)/"page"
            render=subprocess.run(["pdftoppm","-f","1","-l",str(total),"-r",str(DPI),"-png",str(pdf),str(prefix)],
                                  capture_output=True,timeout=30,check=False)
            if render.returncode:return {**base,"code":"OCR_RENDER_FAILED"}
            pages=[]
            for index,image in enumerate(sorted(Path(temp).glob("page-*.png")),1):
                result=subprocess.run(["tesseract",str(image),"stdout","--psm","11","tsv"],
                                      capture_output=True,timeout=20,check=False)
                if result.returncode:
                    pages.append({"page":index,"words":[],"lines":[],"issue":"OCR_PAGE_FAILED"});continue
                records=list(csv.DictReader(io.StringIO(result.stdout.decode("utf-8","replace")),delimiter="\t"))
                width=float(reader.pages[index-1].mediabox.width);height=float(reader.pages[index-1].mediabox.height)
                page_record=next((r for r in records if r["level"]=="1"),None)
                px_width=float(page_record["width"]) if page_record else width*DPI/72
                px_height=float(page_record["height"]) if page_record else height*DPI/72
                words=[]
                for record in records:
                    if record["level"]!="5" or not record["text"].strip():continue
                    left=float(record["left"]);top=float(record["top"])
                    right=left+float(record["width"]);bottom=top+float(record["height"])
                    conf=float(record["conf"])
                    words.append({"text":record["text"],"confidence":round(conf,1),
                                  "pixel_bbox":[left,top,right,bottom],
                                  "bbox":[round(left*width/px_width,2),round(top*height/px_height,2),
                                          round(right*width/px_width,2),round(bottom*height/px_height,2)]})
                lines=_group_words(words)
                pages.append({"page":index,"words":words,"lines":lines,"mean_confidence":
                              round(statistics.mean(w["confidence"] for w in words),1) if words else None})
    except (Exception,) as exc:
        return {**base,"code":"OCR_FAILED","reason":type(exc).__name__,
                "processing_time_ms":round((time.perf_counter()-started)*1000,1)}
    text="\n".join(line["text"] for page in pages for line in page["lines"])
    return {**base,"ok":bool(text.strip()),"page_count":total,"pages":pages,"text":text,
            "chars":len(text),"processing_time_ms":round((time.perf_counter()-started)*1000,1),
            "issues":[] if text.strip() else ["OCR_NO_TEXT"]}
