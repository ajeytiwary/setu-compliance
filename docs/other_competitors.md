Take **publicly documented competitor customer problems** and construct equivalent EuroSetu benchmark scenarios.

## Benchmark A - CarbonChain / Steelforce

This is almost perfect for you.

Steelforce:

- \~€2bn turnover
- exports >2m tonnes/year
- many steel CN codes
- many origins
- many suppliers
- needed CBAM reporting
- needed customs-level data
- needed supplier installation data
- needed EU XML generation
- needed validation

CarbonChain automated its CBAM declarations and validated incoming data. [CarbonChain](https://www.carbonchain.com/case-study/steelforce-cbam?utm_source=chatgpt.com)

### Reproduce this in EuroSetu

Create:

**500 synthetic import lines**

across:

```
CN 7208
CN 7209
CN 7210
CN 7213
CN 7214
CN 7219
CN 7225
...
```

with:

```
India
China
Turkey
South Korea
Brazil
```

and perhaps:

```
20 installations
50 suppliers
10 EU customers
500 shipments
```

Then deliberately introduce:

```
missing installation ID
missing precursor
invalid reporting period
default-value usage
wrong CN code
stale supplier evidence
duplicate installation
missing direct emissions
inconsistent production route
missing verification
```

EuroSetu should ingest everything and produce:

```
500 shipments
↓
472 CBAM-applicable
↓
398 complete
↓
74 blocked
↓
31 supplier-data problems
↓
22 precursor problems
↓
13 classification problems
↓
8 verification problems
```

That immediately looks much more serious.

---

# 4. And you don't need to invent the CBAM data

This is the particularly useful discovery.

The European Commission provides **official filled CBAM examples** for:

- steel blast furnace
- steel EAF
- screws and nuts
- aluminium
- cement
- fertilizers
- hydrogen

as downloadable spreadsheets. [Taxation and Customs Union](https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism/cbam-communication-and-news_en?utm_source=chatgpt.com)

That is gold for EuroSetu.

Use those as **golden test fixtures**.

Your repository should contain something like:

```
tests/
  fixtures/
    eu_cbam/
      steel_blast_furnace/
      steel_eaf/
      screws_nuts/
      aluminium/
      cement/
      fertiliser/
```

Then EuroSetu ingests the Commission example and must calculate exactly the expected output.

That lets you truthfully say:

> **CBAM engine validated against European Commission reference communication examples.**

That's vastly better than saying "our synthetic test passed."

---

# 5. You also have official 2026 calculation datasets

The Commission publishes the definitive-period:

**default values** and **benchmarks**.

The corrected 2026 default values are provided in Excel alongside the legally binding Implementing Regulations, and benchmark values are separately available. [Taxation and Customs Union](https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism/cbam-legislation-and-guidance_en?utm_source=chatgpt.com)

So construct tests:

```
CASE 1
Primary installation data available
→ actual emissions

CASE 2
Primary data unavailable
→ applicable default

CASE 3
Actual > benchmark
→ certificate exposure

CASE 4
Actual < benchmark
→ lower exposure

CASE 5
Default-value regulation version changes
→ historical result preserved
→ new calculation changes
```

That last test proves your **regulation versioning architecture**.

---

# 6. Benchmark B - CarbonChain Spaeter

This is actually an even better commercial demo.

CarbonChain reports that steel trader Spaeter used its scenario analysis to evaluate alternative steel supply chains against a customer's carbon criterion and ultimately won part of a **seven-figure steel deal**. [CarbonChain](https://www.carbonchain.com/case-study/how-spaeter-won-a-7-figure-steel-sale-with-carbonchain-scenario-analysis?utm_source=chatgpt.com)

Create:

```
CUSTOMER RFQ

5,000 t HRC

Buyer requirement:
< X tCO₂e/t

Option A
India BF
€610/t
2.4 tCO₂/t

Option B
India EAF
€660/t
0.8 tCO₂/t

Option C
Turkey EAF
€650/t
0.65 tCO₂/t
```

EuroSetu calculates:

```
                 A       B       C

Material        €3.05m  €3.30m  €3.25m
CBAM exposure   €XXX     €XX      €XX
Tariff          ...
Safeguard       ...
Origin          ...
Evidence        82%      97%      91%

Market access   PASS     PASS     CONDITIONAL

Buyer carbon
criterion       FAIL     PASS     PASS
```

Then:

# **Recommend compliant sourcing scenarios**

Not because EuroSetu is a procurement optimizer yet, but because this demonstrates commercial value.

CarbonChain has already demonstrated that carbon intelligence can contribute directly to winning steel business. [CarbonChain](https://www.carbonchain.com/case-study/how-spaeter-won-a-7-figure-steel-sale-with-carbonchain-scenario-analysis?utm_source=chatgpt.com)

---

# 7. Benchmark C - SAP GTS

Build a deliberately SAP-like transaction.

SAP documents this workflow:

````
Sales order
    ↓
GTS compliance check
    ↓
sanctions
embargo
licence
    ↓
negative result
    ↓
delivery blocked
``` :chatgpt-content-reference{index="10"}


Reproduce the concept:

```text
PO EU-000342

Buyer
Acme GmbH

SKU
HRC-4MM

CN
7208...

Origin
India

Destination
Germany

€487,300
````

Then inject:

```
SANCTIONS = clear
CBAM = pass
ORIGIN = pass
TARIC = pass
QUOTA DATA = stale
```

Result:

```
CONDITIONAL / BLOCKED

Reason
Steel safeguard quota state
cannot be established using
fresh regulatory evidence.

Order value affected
€487,300

Required remediation
Refresh quota state.

Owner
Trade Compliance

Source
TARIC / rule snapshot
```

Then update the data.

EuroSetu recompiles:

```
BLOCKED
    ↓
READY
```

with the complete before/after audit trail.

That's your direct answer to:

> "But SAP already does transaction blocking."

Yes.

**Here is EuroSetu doing the relevant market-access decision from heterogeneous inputs without implementing GTS.**

---

# 8. TARIC gives you another excellent official test dataset

The EU makes raw TARIC data **freely available in Excel** and updates/transmits TARIC data daily.

TARIC includes:

- customs duties
- tariff preferences
- suspensions
- tariff quotas
- antidumping duties
- countervailing duties
- safeguard duties
- prohibitions/restrictions
- supporting-document codes
- nomenclature/additional codes. [Taxation and Customs Union](https://taxation-customs.ec.europa.eu/online-services/online-services-and-databases-customs/eu-customs-tariff-taric_en?utm_source=chatgpt.com)

This means your demo can stop saying:

> synthetic steel quota

and instead execute:

```
shipment
+
CN code
+
origin
+
destination
+
date

↓

TARIC snapshot

↓

applicable measures
```

Then preserve:

```
taric_version
retrieved_at
measure_id
legal_basis
source_hash
valid_from
valid_to
```

This would make EuroSetu substantially more credible.

---

# 9. Benchmark D - SAP preference/origin

This is a harder benchmark and therefore more impressive.

SAP GTS takes BOM information and evaluates originating/non-originating materials against applicable rules of origin. [SAP Learning](https://learning.sap.com/courses/configuring-the-essential-functions-of-sap-global-trade-services/setting-up-preference-determination_a686a8c1-f3c1-45e1-98cb-2e13ec91101b?utm_source=chatgpt.com)

Build a manufactured engineering product:

```
Industrial pump
HS/CN XXXX

BOM

Motor          India       €110
Housing        India        €80
Controller     China        €95
Bearings       Germany      €35
Seal           India        €12
Fasteners      India         €8

Ex-works value             €600
```

Then run:

```
BOM
↓
component classification
↓
origin
↓
applicable origin rule
↓
non-originating materials
↓
transformation/value rule
↓
qualifies / does not qualify
↓
evidence
```

The Commission's free **ROSA** tool provides a useful independent reference: it guides businesses through the product-specific rules of origin under EU trade agreements and produces a self-assessment of preferential eligibility. [Webgate](https://webgate.acceptance.ec.europa.eu/portal9/en/content/how-use-rules-origin-self-assessment-tool-rosa?utm_source=chatgpt.com)

That gives you another external oracle against which to test EuroSetu.

---

# 10. Benchmark E - osapiens

This should test your **multi-regulation architecture**, not CBAM.

OPTIMA Packaging publicly uses osapiens across:

**LkSG + CBAM + CSRD**

within one platform and global supply chain. [Osapiens](https://osapiens.com/en/resources/customer-case-studies/2026/sustainability-reporting-with-the-osapiens-hub-optima-packaging-group?utm_source=chatgpt.com)

Construct a product where the same evidence is consumed by multiple rule families:

```
SUPPLIER
   │
   ├── company identity
   ├── facility
   ├── material
   ├── emissions
   ├── origin
   └── certifications
            │
      ┌─────┼─────┐
      ↓     ↓     ↓
    CBAM  DPP   REACH
```

Then demonstrate:

> changing one evidence object invalidates three downstream claims.

That proves the **evidence graph**, rather than just another collection of compliance modules.

---

# 11. Benchmark F - Carbmee

Carbmee's Everllence case is another good benchmark.

Everllence has roughly €4.3bn revenue and 15,000 employees. Carbmee says the company established audited Scope 3 reporting within weeks, centralized CBAM coordination and began collecting primary emissions data from suppliers. [Carbmee](https://www.carbmee.com/customers/everllences-path-to-supply-chain-carbon-reduction-with-carbmee-eis?utm_source=chatgpt.com)

Your analogous benchmark:

```
ERP purchase data
       +
supplier master
       +
product/BOM
       +
installation data
       ↓
    EuroSetu
       ↓
supplier evidence completeness
       ↓
CBAM completeness
       ↓
orders affected
```

But add the part Carbmee's case isn't centered around:

```
CBAM gap
   ↓
actual EU shipments
   ↓
customer
   ↓
order value
   ↓
€ revenue affected
```

That's the EuroSetu angle.

---

# 12. Benchmark G - supplier-network stress test

CarbonChain has now set a meaningful benchmark here.

Its supplier catalogue publicly says it covers **3,500+ producers**, is based on **2,000+ steel/aluminium intensity datapoints**, supports request-to-share workflows and lets users model costs by supplier, CN code and origin. [CarbonChain](https://www.carbonchain.com/blog/introducing-carbonchain-cbam-supplier-catalogue?utm_source=chatgpt.com)

You cannot claim parity.

Instead test scalability:

```
1,000 suppliers
10,000 products
50,000 evidence objects
100,000 shipments
```

Generate synthetic relational data but use **real regulatory data**.

Measure:

```
ingestion time
compile time
incremental recomputation
evidence lookup
affected-order calculation
regulation update propagation
```

Target, for example:

```
single shipment check       <1 sec
100 shipment batch          <10 sec
10k affected-order lookup   <5 sec
regulation update
impact analysis             <60 sec
```

Those are **engineering targets**, not claims about current performance.

---

# 13. Your benchmark suite should ultimately look like this

I would put these directly in the EuroSetu repository:

| Suite                      | Reference                    | What EuroSetu proves             |
| -------------------------- | ---------------------------- | -------------------------------- |
| **EU-CBAM-GOLDEN**         | European Commission examples | Calculation correctness          |
| **CBAM-2026**              | EU defaults + benchmarks     | Definitive-period implementation |
| **STEELFORCE-STYLE**       | CarbonChain case             | High-volume CBAM workflow        |
| **SPAETER-STYLE**          | CarbonChain case             | Commercial scenario analysis     |
| **SAP-BLOCK**              | SAP GTS documented workflow  | Transaction gating               |
| **SAP-ORIGIN**             | SAP preference workflow      | BOM/origin logic                 |
| **TARIC-LIVE**             | Commission TARIC             | Current trade measures           |
| **ROSA-ORIGIN**            | Access2Markets               | Independent origin validation    |
| **OSAPIENS-CROSSREG**      | osapiens architecture        | Evidence reuse                   |
| **CARBMEE-SUPPLIER**       | Carbmee case                 | ERP → supplier → carbon          |
| **EVIDENCE-DECAY**         | EuroSetu-specific            | Freshness/invalidation           |
| **REGULATION-TIME-TRAVEL** | EuroSetu-specific            | Version reproducibility          |
| **REVENUE-IMPACT**         | EuroSetu-specific            | Commercial prioritisation        |
| **100K-SHIPMENT**          | Synthetic                    | Scalability                      |

This gives you a proper **competitive acceptance suite** rather than a collection of unit tests.

---

# 14. Then expose the results publicly

I'd add a `/benchmarks` page to EuroSetu.

Something like:

```
EUROSETU VALIDATION SUITE

Regulatory engine
──────────────────────────────

EU CBAM reference cases       7/7 PASS
2026 default values          100% PASS
2026 benchmarks              100% PASS

Trade engine
──────────────────────────────

TARIC applicability           PASS
Trade-defence measures        PASS
Supporting documents          PASS
Historical snapshots          PASS

Origin engine
──────────────────────────────

ROSA reference scenarios      18/18 PASS
BOM propagation               PASS
Evidence invalidation         PASS

Evidence engine
──────────────────────────────

Missing evidence              PASS
Expired evidence              PASS
Conflicting evidence          PASS
Superseded evidence           PASS

Commercial engine
──────────────────────────────

Order impact                  PASS
Revenue-at-risk               PASS
Remediation prioritisation    PASS

Scale
──────────────────────────────

100,000 shipments
10,000 products
1,000 suppliers
...
```

But only publish numbers after the automated tests actually establish them.

---

# 15. This also changes the current case study

Right now your public case study says:

> €340k HRC → CBAM precursor incomplete → quota balance required → blocked.

That's a reasonable MVP demonstration, but it doesn't establish much about the underlying engine. [EuroSetu](https://eurosetu.trade/case-study)

I'd turn it into a **five-tab interactive reference case**:

**Order → Rules → Evidence → Decision → Audit**

For every result, allow the prospect to click through:

```
CBAM
FAIL
    ↓
Requirement
CBAM-STEEL-XXX
    ↓
Applicable because
CN 7208...
Origin India
Import into EU
Date ...
    ↓
Required evidence
precursor installation data
    ↓
Available evidence
NONE
    ↓
Legal/regulatory source
Commission Regulation ...
    ↓
Rule version
2026.x
    ↓
Decision
BLOCK
```

And then a button:

**Add missing evidence**

which transitions:

```
BLOCKED → READY
```

while preserving the previous decision.

That is a much stronger demo of the underlying architecture.