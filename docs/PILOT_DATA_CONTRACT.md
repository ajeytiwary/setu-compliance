# JSW Vijayanagar → EU HRC: pilot data contract

The public-record reconstruction proves company, installation, HRC product, BF/BOF route and a verified 2026 EPD. It deliberately does **not** invent a shipment, importer, coil genealogy, CBAM installation dataset or invoice value.

## Minimum private integrations

1. **SAP SD/FI**, EU deliveries, invoices, customer/importer, destination, quantity, value, CN code. Unlocks the value-weighted north-star metric.
2. **SAP MM**, raw-material receipts/consumption, batches, suppliers, origin and purchase orders.
3. **MES**, heat → slab → coil genealogy and production quantities.
4. **EMS/historian**, fuels, process activity and metered observations required by the approved CBAM methodology.
5. **Supplier CBAM feed**, precursor embedded-emissions communications and verification evidence.
6. **Verifier feed**, accredited verifier engagement, findings and statement reference.

CSV contracts are under `connectors/samples/`. Production adapters can use OData/IDoc/API/CDC while preserving the same canonical fields.

## Critical methodology guardrail

The public JSW HRC EPD result is stored as environmental evidence only. It is **not** mapped into `cbam.embedded_emissions`. That field remains missing until CBAM-methodology activity/precursor data and verification are connected.
