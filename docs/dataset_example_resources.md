For EuroSetu, I would therefore build a four-layer benchmark corpus: authoritative regulatory goldens → public real-world documents/data → competitor-derived scenarios → deliberately corrupted synthetic client packs.
Best resources I found
Priority	Resource	What you actually get	Resembles prospective-client data	EuroSetu test
P0	European Commission CBAM filled examples	7 actual XLSX workbooks, including steel BF, steel EAF and screws/nuts	★★★★★	CBAM ingestion + calculation + precursor chains
P0	EC CBAM operator guidance + worked steel example	Detailed BF/BOF production/process/emissions worked example	★★★★★	Reconstruct installation → processes → products → embedded emissions
P0	DocILE benchmark	6,680 annotated real business docs + 100k synthetic docs + ~1M unlabeled docs; invoices/orders with line items	★★★★★	Your document ingestion layer
P0	DocILE GitHub/tools	PDFs, OCR, annotations, synthetic documents, evaluation framework	★★★★★	Invoice/PO extraction accuracy
P0	CarbonChain Steelforce case	Real steel trader CBAM workflow and data requirements	★★★★☆	Reconstruct end-to-end customer scenario
P0	CBAMReturn worked example	Import transactions + supplier files, including intentionally messy supplier spreadsheets	★★★★★	Extremely good ingestion/error-handling scenario
P0	UCI real steel-industry dataset	35,040 real observations: kWh, reactive power, CO₂, load, time	★★★★★	EMS/plant telemetry → evidence/calculation
P0	EU TARIC open-data mirror	Machine-readable tariff/customs snapshots	★★★★★	CN → measures → restrictions → documents
P0	Eurostat COMEXT	Real EU import/export records by commodity/country/month	★★★★★	Generate realistic India→EU steel transaction portfolio
P0	UN Comtrade API	Trade flows, commodity codes, value, quantity, partner, customs/mode fields where available	★★★★☆	Realistic transaction distributions


There are several especially useful secondary sources too. worldsteel's 2026 LCI database is based on data from 160+ sites representing 356 Mt of production and covers 16 steel products; detailed datasets can be requested, while eco-profiles are available directly. World Steel Association voestalpine's downloads provide actual steel EPD PDFs for heavy plate, hot-rolled strip and cold-rolled strip: excellent evidence-document inputs.
For document AI, QUEST/DocILE table dataset adds 954 annotated business-document tables, while CORD supplies 1,000 annotated receipt documents under CC BY 4.0. FUNSD provides 199 noisy scanned forms and ~10,000 semantic entities, although its licensing/use restrictions make it less attractive for your primary commercial test corpus. GitHub
Competitor cases should become tests
The CarbonChain material is particularly valuable because its public cases describe workflows rather than just marketing slogans.
For example, Steelforce says it imports numerous steel CN codes from multiple countries and suppliers, with CarbonChain handling customs-related data, installation-specific information, supplier data and XML generation. CarbonChain
Turn that into:
STEELFORCE-STYLE-001

Inputs
 ├─ 100-500 import transactions
 ├─ 15 CN codes
 ├─ 8 steel suppliers
 ├─ 5 countries
 ├─ customs/import CSV
 ├─ supplier CBAM XLSX
 ├─ installation data
 ├─ precursor emissions
 └─ deliberately incomplete supplier records

EuroSetu must:
 ingest
 ↓
 classify CN
 ↓
 determine CBAM applicability
 ↓
 resolve installation
 ↓
 join supplier evidence
 ↓
 validate evidence
 ↓
 calculate emissions
 ↓
 identify missing data
 ↓
 BLOCK affected shipments
 ↓
 prescribe remediation
 ↓
 ingest corrected evidence
 ↓
 READY
 ↓
 generate declaration/export

That is a perfectly legitimate COMPETITIVE-SCENARIO benchmark. Just don't call its numerical expected result CarbonChain-validated unless CarbonChain published those numbers.
CarbonChain has more cases worth translating. Its case-study catalogue includes Spaeter, Steelforce, Metal Exchange/Pennex, Concord, Gunvor and commodity-finance cases. CarbonChain
For EuroSetu, Spaeter + Steelforce are particularly relevant because one exercises CBAM operations while the other introduces the commercial decision dimension.
An unusually good source: messy CBAM data
The CBAMReturn worked example may actually be more valuable for testing than a polished corporate case study.
It deliberately describes supplier data such as:
"emissions data FINAL v3 (2)"
"Instalation name"
16,50000
"1.9 tCO2e/t"
10-digit TARIC codes
1925 kgCO2e/t instead of tCO2e/t
TOTAL rows
unsaved Excel formulas

This is exactly the sort of garbage a real compliance workflow needs to survive.
I'd create a whole benchmark family from it:
CLIENT-DATA-CHAOS

CHAOS-001 renamed worksheets
CHAOS-002 decimal comma
CHAOS-003 units embedded in cells
CHAOS-004 kg ↔ tonne error
CHAOS-005 8-digit CN vs 10-digit TARIC
CHAOS-006 stale Excel cached formula
CHAOS-007 duplicate supplier
CHAOS-008 conflicting installation IDs
CHAOS-009 missing precursor
CHAOS-010 wrong reporting period
CHAOS-011 expired verification
CHAOS-012 superseded certificate
CHAOS-013 duplicate invoice
CHAOS-014 invoice/PO quantity mismatch
CHAOS-015 MTC heat number mismatch

That would demonstrate something much more commercially interesting than “our formula returned 1.73.”
Academic data is surprisingly useful
The strongest discovery is Terlouw, Harpprecht & Bauer's Steel_CBAM research dataset/code.
It accompanies the 2025 paper “Towards effective carbon accounting for the global steel industry within the EU carbon border adjustment mechanism” and combines regional steel production data with prospective LCA specifically for CBAM.
That should go straight into the EuroSetu research corpus.
The UCI steel dataset is also genuine industrial telemetry rather than generated values: 35,040 observations from a South Korean steel facility covering energy consumption, reactive power, power factor, CO₂ and operational load. It is CC BY 4.0. UCI Machine Learning Repository
Combine those two and you can make a much more convincing mock client:
plant telemetry → emissions evidence → CBAM installation workbook → product → shipment.
Actual evidence documents
Don't limit yourself to datasets. You need PDFs/XLSX/CSV resembling the client's evidence room.
For example, public steel mill certificates exist containing PO number, heat number, dimensions, quantities, weights, tensile/yield strength and chemical composition. One public example is an EN 10204/3.1 certificate with 200 pieces/542 tonnes and multiple heat numbers. Scribd
Combine those with public EPDs such as voestalpine's hot-rolled, cold-rolled and heavy-plate EPDs. Voestalpine
Now you can test:
PO
 ↓
commercial invoice
 ↓
packing list
 ↓
customs declaration
 ↓
CN/TARIC
 ↓
MTC / EN 10204 3.1
 ↓
heat / batch
 ↓
facility
 ↓
EPD / PCF
 ↓
CBAM installation workbook
 ↓
verification evidence
 ↓
EuroSetu evidence graph

That is much closer to the real product.
The corpus I would build
I would stop thinking of this as one “100-transaction demo.” Build a reusable EuroSetu Public Trade Evidence Corpus.
Aim for roughly:
Data	Target
Import transactions	1,000
Commercial invoices	200
Purchase orders	200
Packing lists	100
Customs declarations	100
Supplier CBAM workbooks	50
Mill Test Certificates	50
EPD/PCF documents	30
Facility records	25
Supplier records	50
Energy/EMS records	35,000+
TARIC snapshots	daily/versioned
Regulation snapshots	versioned
Broken evidence chains	200+
Fully clean chains	50+


And give every artifact provenance:
source_type:
 OFFICIAL
 ACADEMIC
 OPEN_DATA
 PUBLIC_COMPANY
 COMPETITOR_CASE
 SYNTHETIC

source_url
license
retrieved_at
sha256
original_filename
synthetic_transform
parent_artifact
expected_use

Then deliberately create corrupted derivatives while retaining the untouched source.
For example:
real public MTC
 │
 ├── original.pdf
 │
 ├── missing_heat_number.pdf
 ├── expired_certificate.pdf
 ├── supplier_name_mismatch.pdf
 └── conflicting_weight.pdf

This gives you a defensible provenance trail for every demo failure.
The demo I'd ultimately show a steel prospect
Don't tell them “we created 100 synthetic rows.”
Give them an evidence room:
EU-STEEL-EXPORT-2026/
│
├── ERP/
│ ├── sales_orders.csv
│ ├── purchase_orders.csv
│ └── suppliers.csv
│
├── LOGISTICS/
│ ├── invoices/
│ ├── packing_lists/
│ └── customs_declarations/
│
├── QUALITY/
│ └── mill_test_certificates/
│
├── CARBON/
│ ├── energy_meter.csv
│ ├── facility_emissions.xlsx
│ ├── cbam_supplier_templates/
│ ├── epds/
│ └── verification/
│
├── REGULATORY/
│ ├── taric/
│ ├── cbam/
│ └── sanctions/
│
└── expected/
 ├── initial_decisions.json
 ├── remediation_actions.json
 └── final_decisions.json

Then EuroSetu discovers, for example:
100 transactions → 27 BLOCKED → €3.8m blocked → 8 root evidence defects → 6 remediation actions → corrected evidence ingested → 100 READY, with every transition clickable back to the source document and regulatory snapshot.
That is far stronger than a conventional SaaS demo because the prospect can hand you their own version of exactly the same document room afterward.
The next logical step is to turn these sources into an actual datasets/public-trade-evidence/ corpus in EuroSetu, with a source manifest, downloader, licenses/provenance, clean originals, corrupted derivatives, and a 100-1,000 transaction integrated steel benchmark. That would also give /benchmarks a “Real-world evidence corpus” section alongside the legal goldens.