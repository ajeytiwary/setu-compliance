from __future__ import annotations
import hashlib,io,json,re,urllib.request
from pathlib import Path
from openpyxl import load_workbook
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/"data"/"official"; OUT.mkdir(parents=True,exist_ok=True)
CBAM_PAGE="https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism/cbam-legislation-and-guidance_en"
DEFAULT_URL="https://taxation-customs.ec.europa.eu/document/download/1c05d211-80cb-4aaa-8ef0-e08005a95d7e_en?filename=DV+correcting+act_final+update_06.08.xlsx"
BENCHMARK_URL="https://taxation-customs.ec.europa.eu/document/download/9877523c-2a02-4926-a211-aefae7cf6d0d_en?filename=CBAM+Benchmarks_20260206.xlsx"
STEEL_URL="https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32026R1457"
def fetch(url):
 req=urllib.request.Request(url,headers={"User-Agent":"SetuCompliance/0.4"});return urllib.request.urlopen(req,timeout=60).read()
def xlsx_rows(raw):
 wb=load_workbook(io.BytesIO(raw),data_only=True,read_only=True);out=[]
 for ws in wb.worksheets:
  rows=list(ws.iter_rows(values_only=True))
  if not rows:continue
  header=[str(x).strip() if x is not None else "" for x in rows[0]]
  out += [{"sheet":ws.title,**{header[i] or f"col_{i}":v for i,v in enumerate(row) if v is not None}} for row in rows[1:]]
 return out
def save(name,source,raw,records):
 obj={"source":source,"sha256":hashlib.sha256(raw).hexdigest(),"records":records};(OUT/name).write_text(json.dumps(obj,indent=2,default=str));return obj
def sync_cbam():
 result={}
 for name,url in (("cbam-defaults-official.json",DEFAULT_URL),("cbam-benchmarks-official.json",BENCHMARK_URL)):
  raw=fetch(url); result[name]={"records":len(save(name,url,raw,xlsx_rows(raw))["records"])}
 return result
def sync_steel():
 raw=fetch(STEEL_URL);html=raw.decode("utf-8","ignore")
 # Archive official act verbatim plus extract category/order/CN candidates for auditable downstream normalization.
 (OUT/"steel-2026-1457.html").write_bytes(raw)
 cats=sorted(set(re.findall(r'>\s*(\d{1,2}(?:\.[AB])?)\s*<',html)))
 orders=sorted(set(re.findall(r'09\.\d{4}',html)))
 cns=sorted(set("".join(x.split()) for x in re.findall(r'\b(?:72|73)\d{2}(?:\s*\d{2}){2}\b',html)))
 return save("steel-2026-1457-extract.json",STEEL_URL,raw,{"categories":cats,"order_numbers":orders,"cn_codes":cns})
if __name__=="__main__":print(json.dumps({"cbam":sync_cbam(),"steel":sync_steel()},indent=2))
