import json
from pathlib import Path
from app.cbam_engine import calculate_actual_steel,steel_cbam_scope
from app.fta_origin import evaluate_origin
ROOT=Path(__file__).resolve().parents[1]
def test_cbam_steel_scope_direct_only():
 assert steel_cbam_scope("72083900")["in_scope"] is True; assert steel_cbam_scope("72083900")["direct_only"] is True; assert steel_cbam_scope("7204")["in_scope"] is False
def test_versioned_cbam_actual_calculation():
 out=calculate_actual_steel(json.loads((ROOT/"examples"/"cbam_actual_steel.json").read_text())); assert out["specific_direct_embedded_emissions_tco2_per_t"]==1.73; assert out["indirect_emissions_audit_tco2"]==84.0; assert out["indirect_emissions_included_tco2"]==0.0; assert out["methodology"]["id"]=="EU_CBAM_2026_2547"
def test_eu_india_fta_not_in_force_means_no_current_preference():
 out=evaluate_origin(json.loads((ROOT/"examples"/"fta_origin_preview.json").read_text())); assert out["legal_regime"]=="CURRENT_MFN"; assert out["preference_available"] is False; assert out["tariff_saving_eur"]==0; assert out["psr_evaluation"] is not None
