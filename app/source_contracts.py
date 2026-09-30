from __future__ import annotations
CONTRACTS={
"taric_measures":{"key":["cn_code","origin_country","measure_type"],"fields":["cn_code","origin_country","measure_type","duty_rate","quota_order_number","additional_code","required_document","valid_from","valid_to","legal_basis"]},
"quota_balances":{"key":["order_number"],"fields":["order_number","balance","unit","as_of"]},
"eucdm":{"key":["data_element"],"fields":["data_element","label","format","cardinality","code_list","procedure"]},
"steel_2026_1457":{"key":["category","origin_country","order_number"],"fields":["category","cn_codes","origin_country","order_number","quota_t","additional_duty_rate","valid_from","valid_to"]},
"cbam_defaults":{"key":["good","country","route"],"fields":["good","cn_code","country","route","direct","indirect","unit","period"]},
"cbam_benchmarks":{"key":["product","route"],"fields":["product","route","benchmark","unit","period"]},
"echa_candidate_list":{"key":["ec_number"],"fields":["name","ec_number","cas_number","reason","included_at"]},
"scip_schema":{"key":["version","picklist","value_code"],"fields":["version","artifact","namespace","picklist","value_code","field","base_field","source_file"]},
"eu_sanctions":{"key":["eu_reference"],"fields":["eu_reference","entity_type","name","aliases","identifiers","programme","legal_basis"]},
"comext_trade":{"key":["period","reporter","partner","product"],"fields":["period","reporter","partner","product","value_eur","net_mass_kg","quantity"]}}
def contract(dataset):return CONTRACTS[dataset]
def validate_record(dataset,row):
 c=contract(dataset);missing=[x for x in c["key"] if row.get(x) in (None,"")]
 return {"valid":not missing,"missing_keys":missing}
