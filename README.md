# Setu Compliance — India → EU Market-Access Control Plane

Setu evaluates an export transaction against the regulatory, evidence and commercial conditions required to sell into Europe. DPP remains a first-class output alongside CBAM and the export package.

## Core pipeline

SAP SD/FI → shipment/order/invoice/value/CN  
SAP MM/PP → material/supplier/origin/BOM  
MES → heat → slab → coil genealogy  
EMS/SCADA → installation/process activity  
Supplier CBAM → precursor emissions  
Verifier → verification state  
→ canonical evidence graph → CBAM + origin + market-access compiler → DPP / CBAM / export package

## Implemented
- Versioned CBAM steel calculation engine (`EU_CBAM_2026_2547`)
- Calculated-vs-verified state and input hashing
- EU–India origin engine with WO/CC/CTH/CTSH/RVC/MAXNOM/specific-process primitives
- Legal guardrail: current negotiated EU–India FTA is not treated as an available preference until effective
- SAP OData live transport
- MES REST transport
- EMS/historian REST transport
- Public DAEWOO steel EMS ingestion path for transport/data-quality testing
- JSW/Vijayanagar deployment profile without fabricated private credentials
- Canonical shipment → genealogy → activity → precursor → verifier pipeline
- DPP, CBAM, FTA/origin, customs and export-market architecture retained

## Production boundary
The repository does **not** claim access to JSW/Tata/SAIL private SAP, MES or EMS systems. Customer endpoints, credentials, approved monitoring plans, plant-specific allocation semantics, verifier access and authoritative product-specific origin rules are required for a real deployment.

## Run locally

    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    uvicorn app.main:app --reload

Open `http://127.0.0.1:8000` and API docs at `/docs`.

## Live connection configuration
Copy `.env.example` to `.env` and configure SAP SD/MM OData, MES REST and EMS REST endpoints. Never commit production credentials.

## 12-week pilot
See [docs/12_WEEK_PLAN.md](docs/12_WEEK_PLAN.md).

The acceptance target is a real €-weighted EU order book where every blocked shipment can be drilled into: country → shipment → coil → rule → missing evidence → supplier/source → owner → remediation, with CBAM/DPP/export outputs generated from the same canonical facts.

## Regulatory guardrail
Setu is engineering assurance infrastructure, not legal certification. Regulatory methodologies and rules must be versioned, source-backed and reviewed when legislation/guidance changes.


## Supplier evidence & remediation

Setu now persists supplier identities, shipment/material links, reusable supplier evidence and evidence requests. A request only resolves against VERIFIED evidence belonging to the same supplier. Resolution recomputes supplier coverage and the blocking SUPPLIER_DATA requirement, creating an auditable blocker → supplier → evidence → readiness loop.

Endpoints: `POST /api/suppliers`, `POST /api/suppliers/{id}/link`, `POST /api/suppliers/{id}/evidence`, `POST /api/remediation/requests`, `POST /api/remediation/requests/{id}/resolve`, `GET /api/remediation`, and `GET /api/evidence-graph`.


## Live EU customs regulatory data

Setu includes provenance-aware adapters for EU Commission TARIC and QUOTA public data. TARIC raw data is published by the Commission and tariff-quota balances are updated daily. Snapshots are hashed and dated; active entitlement consumes a QUOTA balance only when the snapshot is fresh (default: <=1 day). Missing or stale balances produce QUOTA_BALANCE_REQUIRED rather than an assumed in-quota result.

The scheduled GitHub workflow `.github/workflows/sync-eu-regulatory-data.yml` runs daily. Configure direct official Commission export endpoints as repository secrets `EU_QUOTA_CSV_URL` and `EU_TARIC_CSV_URL`, or trigger the workflow manually with URLs. If no direct export URL is configured, the workflow deliberately leaves the prior snapshot untouched so freshness checks fail closed. Runtime/API imports are available under `/api/regulatory/public-data/*`.


## Executable TARIC measure stack

A fresh TARIC snapshot can now be resolved by CN code + origin + import date through `POST /api/customs/taric/resolve`. The engine resolves third-country duty, eligible preference/suspension, tariff-quota treatment, additive anti-dumping/countervailing/safeguard duties, additional codes and required supporting-document conditions. Missing/stale TARIC or QUOTA data blocks entitlement. The result is compiled into `POST /api/compliance/active-entitlement` and exposes `customs_liability_eur`. National VAT/excise are intentionally excluded because they are not contained in TARIC.
