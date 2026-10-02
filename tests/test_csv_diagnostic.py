from scripts.run_csv_diagnostic import diagnose,metrics

def test_csv_diagnostic_public_corpus_shape():
 rows=[
  {"transaction_id":"T1","po_number":"P1","cn_code":"72083900","origin":"IN","destination":"NL","shipment_date":"2026-09-01","quantity_t":"10","line_value_eur":"100000"},
  {"transaction_id":"T2","po_number":"P2","cn_code":"72083900","origin":"IN","destination":"DE","shipment_date":"2026-09-02","quantity_t":"12","line_value_eur":"120000"}]
 good=["COMMERCIAL_INVOICE","CBAM_INSTALLATION_DATA","ORIGIN_DECLARATION","TARIC_SUPPORTING_DOCUMENT"]
 ev=[{"transaction_id":"T1","type":x,"status":"VALID"} for x in good]
 ev += [{"transaction_id":"T2","type":x,"status":"VALID"} for x in good if x!="CBAM_INSTALLATION_DATA"]
 out=diagnose(rows,ev)
 assert out[0]["status"]=="READY_FOR_DIAGNOSTIC_REVIEW"
 assert out[1]["status"]=="BLOCKED"
 m=metrics(out,[{"transaction_id":"T1","accepted":"yes"},{"transaction_id":"T2","accepted":"no"}])
 assert m["blocked"]==1 and m["false_ready"]==0 and m["false_block"]==0
