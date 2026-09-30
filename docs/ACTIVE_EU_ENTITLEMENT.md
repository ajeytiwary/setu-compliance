# Active EU compliance entitlement, regulatory data contract

As of 29 September 2026, EuroSetu treats an entitlement as **active** only when the applicable legal regime is in force and the required dynamic/evidentiary inputs are present.

## Active public-law sources

- Regulation (EU) 2026/1384, EU steel tariff quotas; 18,345,922 t annual total and 50% out-of-quota duty.
- Implementing Regulation (EU) 2026/1457, distribution applicable 1 July–31 December 2026. The checked-in public snapshot includes official CN mappings for category 1A and official India quota/order-number examples for categories 7, 8 and 14.
- Regulation (EU) 2023/956 as amended, definitive CBAM from 1 January 2026.
- Implementing Regulation (EU) 2025/2547, definitive embedded-emissions methodology.
- Implementing Regulation (EU) 2025/2546 and Delegated Regulation (EU) 2025/2551, verification/reporting and reasonable assurance.
- Implementing Regulation (EU) 2025/2620, free-allocation adjustment/benchmarks.
- Implementing Regulation (EU) 2025/2621 corrected by 2026/1740, legally binding default values.

Official Commission information files for defaults and benchmarks are intentionally treated as reference-data imports; the regulations remain the legal source of truth.

## Dynamic public data

Current tariff-quota balances change as customs declarations are allocated. The European Commission QUOTA database publishes current balances. EuroSetu therefore **fails closed** when a balance has not been refreshed: it returns `QUOTA_BALANCE_REQUIRED` instead of assuming quota availability.

## EU–India FTA

The Commission's published 2026 text states that negotiations concluded on 27 January 2026 but that the text is for information, may change during legal revision, becomes final on signature, and becomes binding only after the Parties complete the procedures necessary for entry into force.

Therefore the FTA origin engine can evaluate the negotiated PSR as a scenario, but **cannot create a current preferential customs entitlement**. The active entitlement compiler applies current law/MFN treatment until legal status changes.

## API

`POST /api/compliance/active-entitlement`

Example:

    {
      "payload": {
        "shipment_ref": "EU-001",
        "cn_code": "72083900",
        "origin_country": "IN",
        "import_date": "2026-09-29",
        "customs_value_eur": 2810000,
        "quantity_t": 4100,
        "steel_quota_remaining_t": 5000,
        "quota_balance_as_of": "2026-09-29",
        "importer_cbam_mass_ytd_t": 100,
        "authorised_cbam_declarant": true,
        "cbam_emissions_verified": true
      }
    }

The response returns `ENTITLED` only when all active blocking conditions represented by this compiler pass. It does not purport to replace a customs authority's quota allocation or acceptance of a declaration.
