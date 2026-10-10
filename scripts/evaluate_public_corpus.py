"""Score selected manually annotated public fields and source citations."""
import argparse
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

from app.public_document_ingest import extract_cbam_workbook, extract_public_pdf
from app.pdf_observations import reconcile_documents

ROOT=Path(__file__).resolve().parents[1]

def norm(value):
    value=str(value).strip().upper().replace(",","")
    try:return str(Decimal(value).normalize())
    except InvalidOperation:return value

def evaluate(corpus_dir:Path,workbook:Path|None=None):
    gold=json.loads((ROOT/"data/public_corpus/gold.json").read_text())
    results=[];docs=[];found=total=located=box_count=row_found=row_total=0
    for spec in gold["documents"]:
        path=corpus_dir/f'scribd-{spec["id"]}.pdf'
        if not path.is_file():raise FileNotFoundError(path)
        parsed=extract_public_pdf(path.read_bytes(),path.name)
        obs=parsed["observations"];docs.append({"observations":obs})
        expected=sum(len(v) for v in spec["fields"].values())
        hits=[];misses=[]
        for name,values in spec["fields"].items():
            pred=[f for f in obs["fields"] if f["field"]==name]
            for value in values:
                match=next((f for f in pred if norm(f["raw"])==norm(value)),None)
                if match:
                    hits.append(name+":"+value)
                    if match.get("page") and match.get("line") and match.get("quote"):located+=1
                    if match.get("bbox"):box_count+=1
                else:misses.append(name+":"+value)
        row_hits={kind:sum(len(t["rows"]) for t in obs["tables"] if t["kind"]==kind) for kind in spec.get("rows",{})}
        row_misses=[]
        for kind,expected_rows in spec.get("row_cells",{}).items():
            actual_rows=[row for table in obs["tables"] if table["kind"]==kind for row in table["rows"]]
            for row_index,expected_cells in enumerate(expected_rows):
                for key,value in expected_cells.items():
                    row_total+=1
                    if row_index<len(actual_rows) and norm(actual_rows[row_index].get(key,""))==norm(value):row_found+=1
                    else:row_misses.append(f"{kind}[{row_index}].{key}:{value}")
        found+=len(hits);total+=expected
        results.append({"id":spec["id"],"role":parsed["role"],"source_sha256":obs["sha256"],
                        "selected_field_hits":len(hits),"selected_field_total":expected,"missing":misses,"row_cell_missing":row_misses,
                        "row_counts":row_hits,"expected_row_counts":spec.get("rows",{}),
                        "processing_time_ms":obs["processing_time_ms"]})
    graph=reconcile_documents(docs)
    ids=[x["id"] for x in gold["documents"]]
    links={(ids[e["from"]],ids[e["to"]]) for e in graph["edges"]}
    expected_link=("975352350","975352352")
    negative=("975352350","574284615")
    score={"selected_field_recall":round(found/total,4),"field_hits":found,"field_total":total,
           "page_line_quote_coverage_of_hits":round(located/found,4) if found else 0,
           "bounding_box_coverage_of_hits":round(box_count/found,4) if found else 0,
           "selected_row_cell_accuracy":round(row_found/row_total,4) if row_total else 0,
           "row_cell_hits":row_found,"row_cell_total":row_total,
           "expected_positive_link_present":expected_link in links,
           "expected_negative_link_absent":negative not in links,
           "weight_conflict_detected":any(c["field"]=="net_weight_kg" and set(c["documents"])=={3,4} for c in graph["conflicts"]),
           "documents":results}
    if workbook:
        cbam=extract_cbam_workbook(workbook.read_bytes(),workbook.name)
        products={r["cn_code"]:r for r in cbam["product_rows"]}
        checks={cn:cn in products and abs(products[cn].get("see_total_tco2_per_t",{}).get("raw",-1)-value)<1e-9 for cn,value in gold["cbam_workbook"]["products"].items()}
        score["cbam"]={"source_sha256":cbam["sha256"],"installation_name_correct":any(f["raw"]==gold["cbam_workbook"]["installation_name"] for f in cbam["fields"]),"product_see_total_checks":checks,"processing_time_ms":cbam["processing_time_ms"],"historical_template":True}
    return score

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--corpus-dir",type=Path,required=True);p.add_argument("--cbam-workbook",type=Path)
    args=p.parse_args()
    print(json.dumps(evaluate(args.corpus_dir,args.cbam_workbook),indent=2))
