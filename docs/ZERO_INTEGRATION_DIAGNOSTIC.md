# Zero-integration CSV diagnostic

## Purpose
Get a prospective exporter to first value without SAP/MES/EMS integration. The customer supplies 10–25 or up to ~100 EU-bound shipment/order rows plus the evidence files they already use. EuroSetu returns a triage report with blocked value and evidence gaps.

This is deliberately narrower than the production market-access compiler. `READY_FOR_DIAGNOSTIC_REVIEW` means the minimum diagnostic fields/evidence are present; it does **not** mean customs acceptance, CBAM Registry acceptance, verifier acceptance, preferential-origin entitlement or legal certification.

## Minimum shipment CSV
`transaction_id, po_number, cn_code, origin, destination, shipment_date, quantity_t, line_value_eur`.

Optional evidence JSON uses the public evidence-corpus shape: `transaction_id, type, status`. The first diagnostic gates invoice, CBAM installation data, origin declaration and TARIC supporting evidence.

## Run on the reusable public corpus
```bash
python scripts/build_public_evidence_corpus.py --clean
python scripts/run_csv_diagnostic.py data/public_trade_evidence/evidence_room/transactions.csv \
  --evidence-json data/public_trade_evidence/evidence_room/evidence.json \
  --output diagnostic-report.json
```

The deterministic corpus contains 100 steel transactions, 25 deliberately broken evidence chains and 75 clean chains. It is a workflow/engineering test, not a customer result.

## Real pilot outcome measurement
After the broker/declarant/verifier outcome is known, provide an outcomes CSV:

```csv
transaction_id,accepted
CLIENT-001,true
CLIENT-002,false
```

Then add `--outcomes outcomes.csv`. The report records:
- false-ready: EuroSetu diagnostic review-ready, observed external outcome rejected;
- false-block: EuroSetu blocked, observed external outcome accepted;
- both rates over transactions with observed outcomes.

Do not publish these as customer-performance metrics until the outcome labels come from an authorised real pilot and the case-study wording is approved by the customer.
