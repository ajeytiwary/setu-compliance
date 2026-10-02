"""Content hub: product/workflow/pricing/broker pages, interactive CBAM tools,
guides, worked example, and legal pages.

All regulatory figures trace to versioned sources:
- EU CBAM scope/methodology: app/cbam_engine.py + app/cbam_definitive_v2.py
- Defaults/benchmarks/CSCF: data/cbam/*.json (2025/2621-corr-2026/1740, 2025/2620)
- Steel safeguard: data/eu_steel_measure_2026.json (2026/1384 + 2026/1457)
- Regulation lifecycle: app/regulatory_registry.py
Nothing here invents a rate, default value, or deadline.
"""
from __future__ import annotations

SITE_NAME = "EuroSetu"
TAGLINE = "Market-access control plane for industrial exporters"
CONTACT_EMAIL = "hello@eusetu.trade"
REVIEWED = "2026-10-02"
RULES_BASIS = (
    "Regulation (EU) 2023/956 + Implementing Regulations 2025/2547 (methodology), "
    "2025/2620 (benchmarks/FAA), 2025/2621 corrected by 2026/1740 (defaults), "
    "2025/2546 + 2025/2551 (verification); steel safeguard 2026/1384 + 2026/1457"
)
# Labelled scenario price: caller-supplied by default; this fallback is shown
# wherever a cost illustration needs a number before an official snapshot exists.
SCENARIO_PRICE_EUR = 85.0
SCENARIO_PRICE_LABEL = (
    "Labelled scenario €%.2f/tCO2e - supply your own certificate price snapshot; "
    "registry surrender and authority acceptance remain external." % SCENARIO_PRICE_EUR
)

NAV = [
    ("Product", "/product"),
    ("Workflow", "/workflow"),
    ("Guides", "/guides"),
    ("FAQ", "/faq"),
    ("Tools", "/liability-preview"),
    ("Pricing", "/pricing"),
    ("Brokers", "/brokers"),
    ("Cases", "/case-study"),
    ("Trust", "/trust"),
    ("Benchmarks", "/benchmarks"),
]

SECTORS = [
    ("Iron and steel", "CN 72-73", "Bar, sheet, coil, tube, wire, structures, rail. Includes downstream fasteners (7318), structures (7308), tube (7304-7306). Scrap (7204) and listed ferro-alloys out."),
    ("Aluminium", "CN 76", "Unwrought, plate, foil, profiles, structures. Includes doors, windows, containers and articles (7610-7616). Scrap (7602) out."),
    ("Cement", "CN 25", "Cement, clinker, some kaolinic clays. Child-row defaults apply where supplier data missing."),
    ("Fertilisers", "CN 31 + 28", "Nitrogen fertilisers, ammonia, nitric acid. Pure potassic fertilisers excluded."),
    ("Hydrogen", "CN 2804", "Imported hydrogen. Defaults route-aware; verification per 2025/2546 + 2025/2551."),
    ("Electricity", "CN 2716", "Direct emissions in scope; steel indirect (electricity) audit-only until scope review (2029 earliest)."),
]

TOOLS = [
    ("Liability preview", "/liability-preview", "Price an import ledger line by line on real defaults."),
    ("Threshold checker", "/threshold-checker", "EU 50 t declarant test + UK £50k note, instant read."),
    ("Carbon price relief", "/carbon-price-relief", "Article 9 deduction: what counts and what evidence."),
    ("CBAM rate watch", "/cbam-rate", "How the certificate price works and what to budget."),
]

# 16 qualifying-scheme style list for the EU Article 9 relief page.
# These are carbon-pricing schemes importers most often ask about; qualification
# is per-consignment evidence, not list membership - stated on the page.
CARBON_SCHEMES = [
    "EU Emissions Trading System (EU ETS)",
    "UK Emissions Trading Scheme (UK ETS)",
    "China National Emissions Trading System",
    "Korea Emissions Trading System (K-ETS)",
    "New Zealand Emissions Trading Scheme (NZ ETS)",
    "Swiss Emissions Trading System (CH ETS)",
    "California Cap-and-Trade Program",
    "Canada Federal Output-Based Pricing System (OBPS)",
    "Japan GX-ETS",
    "Kazakhstan Emissions Trading System (KAZ ETS)",
    "Australia Safeguard Mechanism",
    "Singapore Carbon Tax",
    "South Africa Carbon Tax",
    "Chile Carbon Tax",
    "Serbia Carbon Tax",
    "Taiwan Carbon Fee",
]

GUIDES: list[dict] = [
    {
        "slug": "eu-cbam-complete-guide",
        "title": "EU CBAM: the complete guide for Indian exporters",
        "date": "2026-09-28", "read": "14 min read",
        "summary": "Who the EU Carbon Border Adjustment Mechanism catches from 1 January 2026, how the charge is worked out, every deadline, and what to do this quarter - in plain English.",
        "body": """
<h2>Is it definitely happening?</h2>
<p>Yes. The EU Carbon Border Adjustment Mechanism is Regulation (EU) 2023/956, in force with the definitive regime from <b>1 January 2026</b>. The transitional registry period (2023-2025) required quarterly embedded-emissions reports with no certificates; from 2026 importers surrender CBAM certificates against verified emissions. The methodology detail lives in Implementing Regulation (EU) 2025/2547, free-allocation benchmarks in 2025/2620, default values in 2025/2621 corrected by 2026/1740, and verification in 2025/2546 + Delegated Regulation 2025/2551.</p>
<h2>Who gets caught</h2>
<p>Three tests: (1) you are the <b>importer / authorised CBAM declarant</b> for goods released for free circulation in the EU; (2) the goods are <b>CBAM goods</b> - cement, iron &amp; steel, aluminium, fertilisers, electricity and hydrogen per Annex I, with iron &amp; steel reaching downstream codes (fasteners, structures, tube); scrap is broadly out; (3) above the <b>50-tonne per-importer per-calendar-year</b> mass threshold, past which authorised-declarant status and verified embedded emissions are required. <a href="/threshold-checker">Check your position →</a></p>
<h2>How the charge is worked out</h2>
<p><b>CBAM certificates ≈ embedded emissions − free-allocation adjustment − converted carbon-price reduction.</b> Embedded emissions come from <b>actual installation data</b> (calendar-year monitoring, verified) or <b>official default values</b> with a statutory markup (10% in 2026, 20% in 2027, 30% thereafter). Free allocation shrinks yearly via the CBAM factor (0.975 in 2026 → 0 by 2034). Third-country carbon prices reduce the surrender only as a <b>legally converted certificate number with evidence</b> - raw currency values are never converted heuristically. <a href="/liability-preview">Run the preview →</a></p>
<h2>Every deadline that matters</h2>
<ul><li><b>1 Jan 2026</b> - definitive regime starts; certificates accrue on CBAM imports.</li><li><b>2026</b> - first definitive reporting year; monitoring plans and verifier engagement must already exist.</li><li><b>2027</b> - first annual CBAM declaration + surrender cycle for 2026 emissions.</li><li><b>2026-07-01 → 2026-12-31</b> - steel safeguard snapshot (2026/1457) runs alongside CBAM; quota balance is dynamic.</li><li><b>2029 (earliest)</b> - indirect (electricity) emissions review for steel.</li></ul>
<h2>What to do now</h2>
<ol><li>Pull a 12-month EU-bound shipment list with CN codes and masses; run the <a href="/liability-preview">liability preview</a>.</li><li>Confirm authorised-declarant coverage with your EU importer of record.</li><li>Start the supplier conversation - <a href="/guides/supplier-emissions-data">exact ask + email template</a>.</li><li>Assign it to ops/finance with a named owner, not sustainability alone.</li><li>Talk to your broker - they see your commodity codes already. <a href="/brokers">Brokers →</a></li></ol>
""",
    },
    {
        "slug": "defaults-vs-actual-data",
        "title": "Default values vs actual data: the most expensive choice in CBAM",
        "date": "2026-09-26", "read": "8 min read",
        "summary": "Official defaults carry a statutory markup and a one-way character; actual installation data needs monitoring, evidence and verification. How to choose per line.",
        "body": """
<h2>The two data sources</h2>
<p>Every CBAM line uses <b>actual installation emissions</b> (measured over a calendar-year monitoring period, independently verified) or <b>official default values</b> (Implementing Regulation 2025/2621, corrected by 2026/1740). EuroSetu resolves defaults from the checked-in reference table - country-aware, route-aware, with 6-digit then 4-digit CN fallback - and refuses to assert a default entitlement when the table has no row.</p>
<h2>The markup is the price of not knowing</h2>
<p>Defaults are published totals uplifted by a statutory markup: <b>+10% (2026), +20% (2027), +30% (2028+)</b>. On Indian HRC (CN 7208 39 00) the table total 4.28 tCO2e/t becomes a 4.708 certificate-default in 2026. Verified actual intensity for integrated HRC is typically far lower - the gap is usually the biggest number you can move.</p>
<h2>One-way character</h2>
<p>You may use actual data for a final good while using defaults for its precursors - never the reverse. And a declaration filed on defaults cannot later be re-opened with actual data for the same period. Whatever you fail to collect during the year stays uncollected at whatever the default costs you.</p>
<h2>What to do</h2>
<p>Rank suppliers by mass × default intensity (the <a href="/liability-preview">preview</a> does this), chase the top of the list first with the <a href="/supplier-data-template">supplier template</a>, and record verification status per installation - unverified actual data is never silently priced.</p>
""",
    },
    {
        "slug": "supplier-emissions-data",
        "title": "What to ask your suppliers now: CBAM emissions data",
        "date": "2026-09-24", "read": "10 min read",
        "summary": "The exact data CBAM needs from overseas producers, why 2026 data must be collected during 2026, and an email you can send suppliers today.",
        "body": """
<h2>The exact ask</h2>
<p>Per installation and per production route: (1) activity level in tonnes for the calendar-year monitoring period; (2) direct emission sources with factors, oxidation and conversion; (3) precursor quantities with specific embedded emissions and value type (actual/default); (4) monitoring-plan reference; (5) production route; (6) independent verification statement (ISO/IEC 17029 + ISO 14065 family per 2025/2546 + 2025/2551). Electricity data is audit-only for steel until scope changes.</p>
<h2>Why now</h2>
<p>Monitoring periods are calendar years. A supplier who starts measuring in Q3 has already lost half the year - and defaults fill the gap at a markup. The conversation held in Q4 2026 determines the declaration filed in 2027.</p>
<h2>Email you can copy</h2>
<pre class="template">Subject: CBAM emissions data for EU exports - one template, keeps your goods competitive\n\nHi [name],\n\nFrom January 2026 our EU imports carry CBAM certificates on embedded emissions.\nWithout your installation data we must use official defaults (+10% markup),\nwhich raises the landed cost of your goods specifically.\n\nCould you please:\n1. Confirm the installation name + production route for [product/CN]?\n2. Share calendar-2026 activity + emissions per the attached template?\n3. Confirm whether an accredited verifier can verify it (we can suggest one)?\n\nThis directly keeps your goods competitive against suppliers who evidence data.\nThanks,\n[you]</pre>
<p>Get the file: <a href="/supplier-data-template">free supplier data template →</a></p>
""",
    },
    {
        "slug": "carbon-price-relief",
        "title": "Already paid a carbon price abroad? CBAM gives credit for it",
        "date": "2026-09-22", "read": "7 min read",
        "summary": "Article 9 deduction mechanics: effective price, converted certificates, verification, and the evidence kit - with a worked illustration.",
        "body": """
<h2>The mechanics (Article 9)</h2>
<p>The CBAM surrender is reduced by carbon prices <b>effectively paid</b> on the same emissions in the country of origin - ETS allowance cost or carbon tax net of free allocation, rebates and refunds - converted into a number of CBAM certificates under the implementing methodology, capped at the liability. There is no blanket exemption for any origin: EU-origin goods are chargeable like everything else unless a linked scheme applies.</p>
<h2>Worked illustration</h2>
<p>100 t of steel at 2.0 tCO2e/t = 200 tCO2e embedded. At a labelled scenario €85/tCO2e that is €17,000 gross. Evidenced effective carbon price of €20/tCO2e converts to a 200-certificate reduction ≈ €4,000 off - net €13,000. At or above the certificate price, the line can fall to zero; relief never goes negative.</p>
<h2>The evidence kit</h2>
<ol><li><b>Scheme + installation statement</b> - which pricing scheme, which installation, which emissions.</li><li><b>Effective price proof</b> - price actually paid per tCO2e after free allocation/rebates.</li><li><b>Independent verification</b> - verifier statement, not a supplier invoice alone.</li><li><b>Converted certificate figure</b> - the legally converted reduction entered per line.</li></ol>
<p>EuroSetu accepts the reduction only as an already-converted certificate number with evidence; raw currency values block with <span class="mono">CARBON_PRICE_CONVERSION_EVIDENCE_REQUIRED</span> rather than guessing. <a href="/carbon-price-relief">Interactive relief page →</a></p>
""",
    },
    {
        "slug": "steel-safeguard-cost-stack",
        "title": "Steel exporters' 2026 cost stack: safeguard quota and CBAM together",
        "date": "2026-09-20", "read": "8 min read",
        "summary": "Regulation 2026/1384 + Implementing Regulation 2026/1457 quotas run alongside CBAM. How the 50% out-of-quota duty and the certificate surrender interact per tonne.",
        "body": """
<h2>Two charges, one shipment</h2>
<p>Since 1 July 2026, steel above the quarterly country quota pays a <b>50% out-of-quota additional duty</b> on the excess value (2026/1384, implemented per-category by 2026/1457, snapshot through 31 Dec 2026). From 1 January 2026 the same shipment also accrues <b>CBAM certificates</b> on embedded emissions. They stack: duty on value, certificates on carbon.</p>
<h2>What they add up to per tonne</h2>
<p>Take 24 t HRC at €18,400 with 1.9 tCO2e/t verified: CBAM ≈ 45.6 tCO2e minus free-allocation adjustment, times the certificate price. If the quota is exhausted, the same shipment pays 50% on the out-of-quota value share. Quota balance is dynamic public customs data - EuroSetu refuses in-quota treatment (<span class="mono">QUOTA_BALANCE_REQUIRED</span>) until a current balance is supplied or refreshed.</p>
<h2>Three levers that move the total</h2>
<ol><li><b>Quota timing</b> - ship inside quota where the balance allows; watch quarterly resets.</li><li><b>Verified intensity</b> - actual data beats the marked-up default on every tonne.</li><li><b>Carbon-price evidence</b> - converted Article 9 reduction where the origin prices carbon.</li></ol>
<p><a href="/worked-example">See the worked example →</a></p>
""",
    },
    {
        "slug": "cbam-50t-threshold",
        "title": "The 50-tonne CBAM threshold, explained",
        "date": "2026-09-18", "read": "9 min read",
        "summary": "The per-importer per-calendar-year mass test, what counts, worked examples of when import patterns trigger - and the traps.",
        "body": """
<h2>The test</h2>
<p>An importer whose CBAM-goods mass exceeds <b>50 tonnes in a calendar year</b> needs authorised CBAM declarant status and verified embedded emissions for the definitive regime. Below it, no surrender - but the mass still needs tracking, because one more shipment can trip the line mid-year.</p>
<h2>What counts</h2>
<p>Mass of <b>CBAM goods released for free circulation</b> (customs value is irrelevant to this test). Scrap and out-of-scope ferro-alloys do not count; downstream in-scope products (fasteners 7318, structures 7308, tube 7304-7306) do. Returned goods and undischarged special procedures need case-by-case treatment.</p>
<h2>Worked examples</h2>
<ul><li><b>Steady 5 t/month HRC</b> - trips 50 t in October; declarant + verification needed for the year.</li><li><b>One 60 t coil in March</b> - in scope from day one of that consignment.</li><li><b>45 t prime + 40 t scrap</b> - scrap excluded, stays below the line (verify codes first).</li></ul>
<h2>The trap</h2>
<p>The test is per <b>importer of record (legal entity)</b>, not per shipment, per supplier, or per broker. Groups must aggregate per entity. <a href="/threshold-checker">Run the checker →</a></p>
""",
    },
    {
        "slug": "uk-vs-eu-cbam",
        "title": "UK CBAM vs EU CBAM: what's actually different",
        "date": "2026-09-15", "read": "10 min read",
        "summary": "A tax versus a certificate scheme, £50,000 versus 50 tonnes, different deadlines and defaults - a verified side-by-side for businesses facing one or both.",
        "body": """
<h2>Different instruments</h2>
<p>The <b>EU CBAM</b> (Regulation 2023/956, definitive from 1 Jan 2026) is a <b>certificate-surrender scheme</b>: authorised declarants surrender certificates priced off EU ETS auctions, with free-allocation phase-down to 2034. The <b>UK CBAM</b> (Finance Act 2026 Part 5, from 1 Jan 2027) is a <b>tax-style charge</b>: self-assessed per tonne of embodied CO2e at a quarterly sectoral rate, with registration at a <b>£50,000 rolling-12-month / 30-day-forward</b> customs-value threshold, first return and payment 31 May 2028.</p>
<h2>What this means operationally</h2>
<ul><li><b>Scope lists differ</b> - both cover iron &amp; steel, aluminium, cement, fertilisers, hydrogen, but commodity-code edges (scrap exclusions, downstream inclusions) must be checked per regime.</li><li><b>Data strategy converges</b> - both reward verified actual installation data over marked-up defaults, and both make late collection permanent.</li><li><b>Relief differs in form</b> - EU Article 9 certificate reduction vs UK carbon-price-relief deduction; evidence overlaps heavily, so collect once.</li></ul>
<p>EuroSetu's wedge is the <b>India → EU</b> corridor (EU engine live today); the same evidence graph serves UK-bound books when needed. <a href="/liability-preview">Preview EU liability →</a></p>
""",
    },
    {
        "slug": "verification-guide",
        "title": "CBAM verification: what verifiers actually check",
        "date": "2026-09-12", "read": "9 min read",
        "summary": "Accreditation, monitoring-plan conformity, system boundaries, precursor evidence and the verification statement - per 2025/2546 + 2025/2551.",
        "body": """
<h2>The standard</h2>
<p>Actual embedded-emissions values must be verified by an <b>accredited verifier</b> against the monitoring methodology (2025/2547) under the verification rules (2025/2546) and accreditation requirements (Delegated Regulation 2025/2551, ISO/IEC 17029 + ISO 14065 family). Unverified actual data is not priced - EuroSetu holds it as <span class="mono">CALCULATED_UNVERIFIED</span> until the statement lands.</p>
<h2>What gets checked</h2>
<ul><li><b>Monitoring-plan conformity</b> - sources, factors, oxidation/conversion, boundaries as approved.</li><li><b>Activity data</b> - production tonnes per route, reconciled to plant records.</li><li><b>Precursor evidence</b> - quantities × specific embedded emissions, value type per precursor.</li><li><b>Materiality</b> - misstatements above the materiality threshold fail verification.</li></ul>
<h2>How to pass first time</h2>
<p>Engage the verifier before the monitoring year ends, keep the evidence vault per supplier line with SHA-256 checksums, and never re-key supplier files - parse them with provenance (sheet, cell, heading) so every problem comes back as a plain-English fix note.</p>
""",
    },
    {
        "slug": "authorised-declarant-registration",
        "title": "Authorised CBAM declarants: registration without surprises",
        "date": "2026-09-10", "read": "7 min read",
        "summary": "Who must hold authorised-declarant status, what the registry asks for, and the records to keep from day one.",
        "body": """
<h2>Who registers</h2>
<p>Any importer whose CBAM-goods mass exceeds 50 t in a calendar year needs <b>authorised CBAM declarant</b> status via the CBAM registry; only authorised declarants may lodge CBAM declarations and surrender certificates. Customs declarants acting indirectly need authorisation paths mapped before the first in-scope consignment.</p>
<h2>What the file needs</h2>
<p>EORI, establishment, contact and compliance history, plus the monitoring and data-collection arrangements behind the declaration. Until the registry interaction completes, EuroSetu flags <span class="mono">CBAM_DECLARANT_AUTHORISATION</span> as a blocker rather than assuming coverage.</p>
<h2>Records from day one</h2>
<p>Keep per-consignment CN codes, masses, origins, values, supplier declarations with monitoring-period and verification references, and the audit trail of every save, upload and export - six-year horizon. The <a href="/product">records vault</a> files each document against its supplier line with checksums and a completeness view.</p>
""",
    },
]

GUIDE_INDEX = {g["slug"]: g for g in GUIDES}

WORKED_LEDGER = [
    {"mrn": "MRN-001", "date": "2027-01-15", "cn": "72083900", "desc": "Hot-rolled coil", "mass_t": 24.0, "value": 18400, "supplier": "Anhui Steel", "file": "tidy template, verified"},
    {"mrn": "MRN-002", "date": "2027-02-20", "cn": "73181500", "desc": "Bolts", "mass_t": 3.2, "value": 9500, "supplier": "Anhui Steel", "file": "same declaration, precursor inside"},
    {"mrn": "MRN-003", "date": "2027-03-05", "cn": "76011000", "desc": "Primary aluminium", "mass_t": 18.0, "value": 42000, "supplier": "Baotou Alu", "file": "messy file, unverified"},
    {"mrn": "MRN-004", "date": "2027-03-28", "cn": "76020000", "desc": "Aluminium scrap", "mass_t": 12.0, "value": 8000, "supplier": "-", "file": "not in CBAM goods table"},
    {"mrn": "MRN-005", "date": "2027-04-11", "cn": "72041000", "desc": "Ferrous scrap", "mass_t": 5.0, "value": 3000, "supplier": "-", "file": "explicit exclusion"},
    {"mrn": "MRN-006", "date": "2027-04-02", "cn": "25231000", "desc": "Cement clinker", "mass_t": 30.0, "value": 4100, "supplier": "-", "file": "covered, no supplier data yet"},
]


def shell(title: str, desc: str, body: str, extra_head: str = "") -> str:
    nav = "".join(f'<a href="{h}">{t}</a>' for t, h in NAV)
    tools = "".join(f'<a href="{h}">{t}</a>' for t, h, _ in TOOLS)
    sectors = "".join(f"<li><b>{n}</b> ({c}): {d}</li>" for n, c, d in SECTORS)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} - EuroSetu</title><meta name="description" content="{desc}">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/public.css">
<script src="/public.js" defer></script>
<style>
.guide-list{{display:grid;gap:14px;margin-top:26px}}
.guide-card{{border:1px solid var(--line);border-radius:var(--radius);background:var(--card);padding:22px;box-shadow:var(--shadow)}}
.guide-card h3{{margin:6px 0 8px}}.guide-card h3 a{{text-decoration:none}}.guide-card h3 a:hover{{color:var(--green)}}
.meta{{font-size:12px;color:var(--muted);font-weight:700;letter-spacing:.04em}}
.tool-grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:16px;margin-top:24px}}
.tool-grid article{{border:1px solid var(--line);border-radius:var(--radius);background:var(--card);padding:24px}}
.form-card{{border:1px solid var(--line);border-radius:var(--radius);background:var(--card);padding:26px;box-shadow:var(--shadow);margin-top:24px}}
.form-card label{{display:block;font-size:13px;font-weight:700;margin:14px 0 4px}}
.form-card input,.form-card select,.form-card textarea{{width:100%;border:1px solid var(--line);border-radius:var(--radius-btn);padding:11px 12px;font:inherit;background:#fff;color:var(--ink)}}
.form-card textarea{{min-height:120px;font-family:ui-monospace,monospace;font-size:13px}}
.btn{{display:inline-block;background:var(--ink);color:#fff;border:1px solid var(--ink);border-radius:var(--radius-btn);padding:12px 20px;font-weight:750;cursor:pointer;font-size:15px;margin-top:16px;text-decoration:none}}
.btn:hover{{background:var(--green);border-color:var(--green)}}
.result{{margin-top:22px;border:1px solid var(--line);border-radius:var(--radius);overflow-x:auto}}
.result table{{width:100%;border-collapse:collapse;font-size:13.5px}}
.result th,.result td{{border-bottom:1px solid var(--line);padding:9px 11px;text-align:left;vertical-align:top}}
.result th{{background:var(--cream);font-size:12px;letter-spacing:.04em}}
.mono{{font-family:ui-monospace,monospace;font-size:12.5px;overflow-wrap:anywhere}}
.pill{{display:inline-block;font-size:11px;font-weight:800;letter-spacing:.06em;border:1px solid var(--line);border-radius:var(--radius-chip);padding:3px 9px;background:var(--cream)}}
.pill.ok{{color:var(--green);border-color:var(--green)}}.pill.warn{{color:var(--amber);border-color:var(--amber)}}.pill.bad{{color:var(--red);border-color:var(--red)}}
pre.template{{background:#091a15;color:#eef7f2;border-radius:var(--radius);padding:20px;overflow-x:auto;font-size:13px;white-space:pre-wrap}}
.steps{{display:grid;gap:14px;margin-top:24px}}
.steps article{{border:1px solid var(--line);border-radius:var(--radius);background:var(--card);padding:24px}}
.steps b.step{{font-size:12px;color:var(--green);letter-spacing:.08em}}
.faq details{{border:1px solid var(--line);border-radius:var(--radius-btn);background:var(--card);padding:14px 18px;margin-top:10px}}
.faq summary{{font-weight:750;cursor:pointer}}
.disclaimer{{border-left:3px solid var(--amber);background:#fdf8ec;border-radius:0 var(--radius-btn) var(--radius-btn) 0;padding:14px 18px;margin-top:22px;font-size:14px}}
@media(max-width:860px){{.tool-grid{{grid-template-columns:1fr}}}}
</style></head>
<body><nav><a class="brand" href="/">EUROSETU</a><div class="navlinks">{nav}</div><a class="button small" href="/demo">Request demo access →</a></nav>
<main>{body}</main>
<footer><div class="brand">EUROSETU</div><p>Market-access infrastructure for industrial trade. Contact: <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a></p><p><a href="/product">Product</a> · <a href="/workflow">Workflow</a> · <a href="/guides">Guides</a> · <a href="/faq">FAQ</a> · <a href="/sectors">Covered sectors</a> · <a href="/liability-preview">Tools</a> · <a href="/pricing">Pricing</a> · <a href="/brokers">Brokers</a> · <a href="/account">Account</a> · <a href="/worked-example">Worked example</a> · <a href="/supplier-data-template">Supplier template</a></p><p><a href="/privacy">Privacy</a> · <a href="/terms">Terms</a> · <a href="/dpa">Data processing</a> · <a href="/security">Security</a> · <a href="/changelog">Rules changelog</a></p><p class="muted">© 2026 EuroSetu. Engineering assurance infrastructure, not legal advice, customs authority acceptance or verifier accreditation. Rules basis reviewed {REVIEWED}.</p></footer>
{extra_head}
</body></html>"""


def hero(eyebrow: str, h1: str, copy: str) -> str:
    return f'<section class="hero"><p class="eyebrow">{eyebrow}</p><h1>{h1}</h1><p class="hero-copy">{copy}</p></section>'
