# Add or replace a data provider

1. Keep the logical dataset ID stable (for example `taric_measures`).
2. Add a provider entry to `config/data_sources.json` with a unique id, parser kind, trust class and URL.
3. Add a specialized adapter only when the source is an API, landing-page distribution, ZIP/XML family or other non-generic format.
4. Normalize into `app/source_contracts.py`; engines consume the normalized contract, never provider-specific fields.
5. Validate keys, minimum record counts, effective dates and source hash before publishing.
6. For authority-required datasets, MIRROR and DEMO_ONLY providers cannot satisfy a production gate.
7. Keep the old provider disabled rather than deleting it until snapshot equivalence has been checked.

This makes source replacement a configuration/adapter change rather than a regulatory-engine rewrite.
