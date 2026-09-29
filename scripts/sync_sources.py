from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.source_sync import sync_many
DEFAULT=["taric_measures","eucdm","echa_candidate_list","scip_schema","eu_sanctions"]
def main():
 ap=argparse.ArgumentParser(description="Download, hash, normalize and validate Setu regulatory sources")
 ap.add_argument("datasets",nargs="*",default=DEFAULT)
 ap.add_argument("--strict",action="store_true",help="exit non-zero if any source fails")
 a=ap.parse_args();r=sync_many(a.datasets);print(json.dumps(r,indent=2,default=str))
 if a.strict and not all(x["ok"] for x in r.values()):return 1
 return 0
if __name__=="__main__":raise SystemExit(main())
