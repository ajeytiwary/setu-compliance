from pathlib import Path
from app.db import init_db
from app.integrations import CONNECTORS,import_sample,parse_csv,validate_records,canonical_summary
def test_all_connector_samples_validate():
 init_db(); root=Path(__file__).resolve().parents[1]
 for code,spec in CONNECTORS.items():
  parsed=parse_csv(spec,(root/"connectors"/"samples"/spec.sample).read_text()); good,errors=validate_records(spec,parsed); assert good,f"{code} sample has no usable records"; assert not errors,f"{code}: {errors}"
def test_import_sample_creates_canonical_record():
 init_db(); out=import_sample("mes"); assert out["status"]=="SUCCESS"; assert out["rows_accepted"]>=1; assert canonical_summary()["genealogy_edges"]>=1
