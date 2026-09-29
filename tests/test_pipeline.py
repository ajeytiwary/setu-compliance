from app.db import init_db
from app.integrations import import_sample
from app.steel_pipeline import assemble_shipment,evaluate_shipment_cbam,evaluate_shipment_origin
def test_canonical_pipeline_assembles_and_calculates():
 init_db()
 for c in ["sap_sd","sap_mm","mes","ems_activity","supplier_cbam","verifier"]:import_sample(c)
 a=assemble_shipment("DEMO-EU-001"); assert a["completeness"]["sap"]; assert a["completeness"]["genealogy"]; assert a["completeness"]["ems"]
 cbam=evaluate_shipment_cbam("DEMO-EU-001"); assert cbam["result"]["specific_embedded_emissions_tco2_per_t"]>0
 origin=evaluate_shipment_origin("DEMO-EU-001"); assert origin["result"]["legal_regime"]=="CURRENT_MFN"; assert origin["result"]["tariff_saving_eur"]==0
