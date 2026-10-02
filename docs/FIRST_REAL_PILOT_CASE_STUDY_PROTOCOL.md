# First real pilot case-study protocol

## Claim boundary
Do not publish a customer-performance case study until the exporter has authorised the use of the results. Public/open and synthetic evidence may demonstrate workflow behaviour only.

## Pilot cohort
Start with 10–25 EU-bound steel shipments from one exporter. No SAP integration is required for phase 1: accept a bounded CSV export and the evidence pack already used with the EU buyer/importer, broker or declarant.

## Baseline before EuroSetu
For every shipment record: external submission/acceptance state, known compliance blockers, remediation requested by buyer/broker/declarant/verifier, and order value. Freeze this baseline before revealing EuroSetu's result.

## Blind evaluation
Run the CSV diagnostic and then the full configured market-access compiler where sufficient evidence exists. Preserve the exact code commit, rule/source snapshots, evidence hashes and decision hashes.

## Outcome labels
After the external process resolves, label each shipment:
- ACCEPTED_WITHOUT_DATA_REMEDIATION
- ACCEPTED_AFTER_DATA_REMEDIATION
- REJECTED_OR_HELD_FOR_DATA
- OUTCOME_PENDING

False-ready = EuroSetu positive state followed by rejection/hold for a compliance-data reason in scope.
False-block = EuroSetu blocked state but the external process accepted without the flagged remediation.
Do not count pending outcomes.

## Publishable case-study fields
Number and € value of shipments; initial blocked/positive split; genuine previously unknown blockers; false-ready/false-block counts and rates; median time to identify blocker; median remediation time; € value moved from blocked to positive; top blocker classes; customer-approved quote.

## Success threshold for first case
The first pilot is evidence-generating, not a marketing pass/fail exercise. Publish the confusion matrix and failure modes even if imperfect. The product decision is whether errors are explainable and whether remediation materially improves the customer's current process.
