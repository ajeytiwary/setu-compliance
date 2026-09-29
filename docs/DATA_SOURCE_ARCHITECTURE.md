# Pluggable regulatory and demo data sources

Setu engines consume stable logical dataset IDs, never vendor URLs. `config/data_sources.json` maps each dataset to ordered providers.

Trust classes:
- LEGAL: authentic legal text; may define binding rules.
- OFFICIAL: authority-published operational/reference data.
- OFFICIAL_STATISTICS: official contextual statistics, not a compliance rule.
- MIRROR: convenience copy; never upgrades legal authority.
- DEMO_ONLY: synthetic/research data; never satisfies a regulatory evidence gate.

A provider may be replaced or disabled without changing a rule engine. Versioned snapshots retain provider, source URL, SHA-256, record count and HTTP provenance. Landing-page providers deliberately return DISCOVERY_REQUIRED: a sync job must resolve the authority's current downloadable distribution before publishing data.

Fail closed: authority-required datasets cannot be silently substituted by MIRROR or DEMO_ONLY providers. Mirrors can support development and continuity checks, but a production regulatory decision must retain an official/legal snapshot.
