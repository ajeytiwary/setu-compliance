# KPI contract

## North-star: Auto-compliance-ready EU-bound value %

Denominator: invoiced/contracted EUR value of all EU-bound shipments in the selected period.

Numerator: value of shipments for which **every blocking rule applicable at the shipment date** evaluates PASS using machine-ingested canonical data or accepted verified evidence, without a human needing to assemble the export compliance pack.

A shipment with 99% evidence completeness but one blocking requirement missing contributes **zero** to the numerator.

## Evidence completeness %
For each requirement: `min(evidence present, evidence required) / evidence required`. Portfolio KPI is shipment-value weighted.

## Supplier-data coverage %
`complete required suppliers / required suppliers`, value weighted across shipments.

## Verification cycle time
Calendar days from verification engagement start to completed verification. Portfolio KPI is median.

## Manual compliance hours / shipment
Total human time explicitly logged against compliance preparation divided by shipment count.
