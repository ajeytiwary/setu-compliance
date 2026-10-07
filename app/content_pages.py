"""Page builders + tool APIs for the content hub. All figures trace to
versioned engines/tables; see content_hub.py header."""
from __future__ import annotations
from .content_hub import (
    shell, hero, GUIDES, GUIDE_INDEX, WORKED_LEDGER, CARBON_SCHEMES,
    NAV, TOOLS, SITE_NAME, CONTACT_EMAIL, REVIEWED, RULES_BASIS,
    SCENARIO_PRICE_EUR, SCENARIO_PRICE_LABEL,
)

CBAM_FACTOR_TABLE = {2026: 0.975, 2027: 0.95, 2028: 0.90, 2029: 0.775, 2030: 0.625, 2031: 0.475, 2032: 0.325, 2033: 0.175, 2034: 0.0}


def _cta_row() -> str:
    return f'''<section class="cta-band"><h2>See it on your own shipments</h2>
<p>Run the CBAM liability preview on your 12-month EU-bound list, or get demo access to the full control plane - TARIC duty, safeguard quota, origin, sanctions and evidence.</p>
<p><a class="btn" href="/liability-preview">Run liability preview →</a>
<a class="btn" href="/demo" style="margin-left:10px">Request demo access →</a></p></section>'''


def _rules_footer() -> str:
    return f'''<div class="disclaimer"><b>Rules basis (reviewed {REVIEWED}):</b> {RULES_BASIS}.
Certificate cost illustrations use a {SCENARIO_PRICE_LABEL}</div>'''


# ---------------------------------------------------------------- pages

def product_page() -> tuple[str, str]:
    body = hero("PRODUCT", "The market-access control plane for industrial exports",
        "One shipment. Every requirement - customs duty (TARIC), steel safeguard quota, CBAM certificates, origin, sanctions, and the evidence behind each. CBAM is the live wedge module; the plane covers the rest. Built for the India → EU steel corridor first.")
    body += '''<section><h2>What it does</h2><div class="tool-grid">
<article><h3>🧭 Compile obligations</h3><p>Start with product, CN code, origin, destination, facility and date. EuroSetu determines which rule families apply - TARIC duty, safeguard quota, CBAM, origin, sanctions - and which evidence each needs.</p></article>
<article><h3>🔍 TARIC duty</h3><p>Third-country duty, preferences, suspensions, tariff quotas, trade-defence and restrictions resolved per line on versioned snapshots - with missing-document and prohibition blockers, never silent passes.</p></article>
<article><h3>🛡️ Safeguard quota</h3><p>Steel quota balance checked before any in-quota treatment is asserted. Out-of-quota duty and CBAM certificates stack per tonne - both shown, neither guessed.</p></article>
<article><h3>🌍 Origin preview</h3><p>EU-India FTA is negotiated, not in force: the engine returns CURRENT_MFN today and previews technical origin so the preference claim is ready at entry into force.</p></article>
<article><h3>🚫 Sanctions screen</h3><p>Direct-match, 50%-ownership and control screening with freshness blockers. A listed owner anywhere in the chain blocks the order before it ships.</p></article>
<article><h3>🕸️ Evidence graph</h3><p>Shipment requirement → supplier → evidence request → verified evidence → readiness. Verify once, permission-share many. Missing information stays visible instead of silently passing.</p></article>
<article><h3>📥 Load your imports</h3><p>Paste a 12-month EU-bound shipment list - CN codes, masses, values, origins. CSV up to 8&nbsp;MB, processed in your browser session and never stored by the preview tool.</p></article>
<article><h3>🔗 Supplier portal</h3><p>Each supplier gets a scoped upload link: one installation, one monitoring period, one evidence type. No logins to provision, no full-system access. Links expire; every file lands checksummed (SHA-256) against its line.</p></article>
<article><h3>🧮 CBAM liability engine (live wedge)</h3><p>Every line priced on versioned EU tables - defaults (2025/2621 corr. 2026/1740) with statutory markup, benchmarks (2025/2620), CSCF, CBAM factor - via the same engines that power the pilot. Unverified actual data is held, never silently priced.</p></article>
<article><h3>🗂️ Records vault</h3><p>Supplier declarations, monitoring-plan refs, verification statements and carbon-price evidence filed per line with checksums and a completeness view. Six-year retention horizon from day one.</p></article>
<article><h3>📊 Threshold monitor</h3><p>Per-importer mass tracked against the 50&nbsp;t calendar-year test with an 80% early warning. One more shipment never trips the line by surprise.</p></article>
<article><h3>📦 Declaration pack</h3><p>Annual declaration figures, per-line value type (actual/default), verification status and audit log exported as a zip - ready for your declarant, verifier and auditor.</p></article>
</div></section>
<section><h2>Roles and access</h2><p>Owner, ops, finance and read-only auditor roles. Supplier links are scoped to a single evidence request. Every save, upload, calculation and export is written to the audit log with actor and timestamp.</p></section>
<section><h2>Security</h2><p>Least-privilege access, per-request tokens, SHA-256 checksums on every document, and full audit trails. <a href="/security">Security detail →</a></p></section>'''
    body += _cta_row() + _rules_footer()
    return ("Product: EuroSetu market-access control plane", "TARIC duty, safeguard quota, CBAM wedge, origin, sanctions and evidence graph for India-EU steel.", body)


def workflow_page() -> tuple[str, str]:
    body = hero("WORKFLOW", "From order to market-access answer in three steps",
        "The same three steps whether you run the free CBAM preview or the full control plane - CBAM is the worked path below; TARIC, quota, origin, sanctions and evidence ride the same rails.")
    body += '''<section class="steps">
<article><b class="step">STEP 1 - COMPILE OBLIGATIONS</b><h3>List what you ship</h3><p>Paste or upload 12 months of EU-bound lines: CN code, mass, value, origin country. The preview parses them in-session and flags out-of-scope lines (scrap, non-CBAM codes) immediately. The control plane goes further: TARIC measures, safeguard quota category, CBAM scope, origin rule, sanctions parties - one obligation list per shipment.</p></article>
<article><b class="step">STEP 2 - TRACE EVIDENCE</b><h3>Chase only what moves the number</h3><p>CBAM lines rank by mass × default intensity so the top suppliers get the ask first. Each gets a scoped portal link with the exact template - installation, route, monitoring period, verification. Tidy files parse with provenance; messy files come back as plain-English fix notes. The same graph carries mill certs, origin statements and quota documents.</p></article>
<article><b class="step">STEP 3 - PRICE, PRIORITISE, PACK</b><h3>Liability per line, blockers by money</h3><p>Actual data where verified, marked-up defaults where not, free-allocation adjustment and converted carbon-price reduction per CBAM line; duty plus quota treatment per customs line. Threshold monitor watches 50&nbsp;t; the declaration pack exports everything your declarant needs - and remediation ranks by revenue at risk, not document count.</p></article>
</div></section>
<section><h2>Who does what</h2><p><b>Ops</b> owns the shipment list and supplier chase. <b>Finance</b> owns the certificate budget. <b>Sustainability</b> owns monitoring plans and verifier engagement. <b>Brokers</b> see commodity codes already - <a href="/brokers">bring them in →</a></p></section>'''
    body += _cta_row() + _rules_footer()
    return ("Workflow - EuroSetu", "Compile obligations, trace evidence, price and prioritise: the EuroSetu workflow with CBAM as the worked path.", body)


def pricing_page() -> tuple[str, str]:
    body = hero("PRICING", "Start with a reviewed steel evidence diagnostic.",
        "A fixed-scope engagement on your own shipments, with source-linked findings and human review.")
    body += '''<section><div class="tool-grid">
<article><h3>Diagnostic - scoped proposal</h3><p>We agree the shipment set, document types, review effort and deliverables before quoting. The output is a source-linked exception register, reconciliation findings and remediation plan.</p></article>
<article><h3>Design-partner pilot - scoped proposal</h3><p>Run real shipments with named reviewers, an agreed acceptance test and a signed data-handling agreement. The pilot does not imply that a customs authority or verifier has accepted a declaration.</p></article>
<article><h3>Recurring platform - not yet for sale</h3><p>Production subscriptions open only after a real same-shipment dossier has reached an auditable, reviewer-approved READY decision and tenant isolation, recovery and operational acceptance tests have passed.</p></article>
</div><p style="margin-top:18px">Synthetic demonstrations are labelled as such. Actual-data calculations and release decisions require verified source evidence and human approval.</p></section>'''
    body += _cta_row() + _rules_footer()
    return ("Pricing - EuroSetu", "Reviewed diagnostics and design-partner pilots; production subscription release gate.", body)


def brokers_page() -> tuple[str, str]:
    body = hero("FOR BROKERS", "Your clients' market-access problem is already in your inbox",
        "You see their commodity codes, masses and origins on every customs file. EuroSetu turns that visibility into a service line - CBAM first, then duty, quota, origin and sanctions on the same dashboard.")
    body += '''<section><h2>Three ways to work together</h2><div class="tool-grid">
<article><h3>Referral</h3><p>Introduce clients; we run the diagnostic and pilot. You get visibility on their readiness and a referral fee. No delivery burden.</p></article>
<article><h3>White-label</h3><p>Run the liability preview and supplier chase under your brand. Your clients see your portal; EuroSetu powers the engines and rule updates underneath.</p></article>
<article><h3>Wholesale</h3><p>Buy platform capacity for your book and bundle market-access readiness with clearance. One dashboard across all your importers' thresholds, quota positions and declaration packs.</p></article>
</div></section>
<section><h2>Why brokers win this</h2><p>Market-access data collection starts from the customs file you already hold. The broker who brings the 50-tonne warning, the quota timing and the supplier template keeps the client; the broker who waits gets the panicked call in April 2027.</p>
<p><a class="btn" href="/demo">Become a partner →</a></p></section>'''
    body += _rules_footer()
    return ("Brokers - EuroSetu partner programme", "Referral, white-label and wholesale paths for customs brokers.", body)


def liability_page() -> tuple[str, str]:
    body = hero("TOOLS · CBAM WEDGE", "CBAM liability preview",
        "The live wedge module: paste your EU-bound shipment lines. Each CBAM line is priced on the real default/benchmark tables with the statutory markup - in your browser session, nothing stored. TARIC duty, quota, origin and sanctions run in the pilot on the same ledger.")
    body += '''<section class="form-card"><h2>Your shipment lines</h2>
<p class="meta">ONE LINE PER ROW · FORMAT: CN CODE, MASS (T), VALUE (€, OPTIONAL), ORIGIN (OPTIONAL, DEFAULT IN)</p>
<label for="ledger">Shipment ledger</label>
<textarea id="ledger" placeholder="72083900, 24, 18400, IN&#10;73181500, 3.2, 9500, IN&#10;76011000, 18, 42000, IN&#10;76020000, 12, 8000"></textarea>
<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px">
<div><label for="year">Reporting year</label><select id="year"><option>2026</option><option>2027</option><option>2028</option></select></div>
<div><label for="price">Certificate price €/tCO₂e (your snapshot)</label><input id="price" value="85" inputmode="decimal"></div>
<div><label for="origin">Default origin</label><input id="origin" value="IN"></div>
</div>
<button class="btn" id="run">Price my ledger →</button>
<div class="result" id="out" style="display:none"></div>
<p class="meta" style="margin-top:14px">SCOPE: IRON &amp; STEEL + ALUMINIUM + CEMENT LINES PRICED ON CHECKED-IN TABLES. SCRAP AND OUT-OF-SCOPE CODES ARE FLAGGED, NOT PRICED. UNVERIFIED ACTUAL DATA IS NEVER ASSUMED - USE DEFAULTS UNTIL VERIFIED.</p>
</div></section>
<section class="faq"><h2>How the maths works</h2>
<details><summary>Where do the emission factors come from?</summary><p>Official default values (2025/2621 corrected by 2026/1740), resolved country- and route-aware with 6-digit then 4-digit CN fallback, plus the statutory markup (10% 2026 / 20% 2027 / 30% 2028+). Missing rows block with DEFAULT_NOT_FOUND instead of guessing.</p></details>
<details><summary>What about free allocation?</summary><p>Benchmarks (2025/2620) × CBAM factor × CSCF, deducted per tonne. 2026 factor 0.975, falling to zero by 2034.</p></details>
<details><summary>Is the certificate price official?</summary><p>No - you supply the snapshot (default shown: labelled scenario €85). Registry surrender and authority acceptance remain external.</p></details>
</section>'''
    body += _rules_footer()
    extra = '''<script>
document.getElementById('run').onclick = async () => {
  const out = document.getElementById('out'); out.style.display='block'; out.innerHTML='<p style="padding:18px">Pricing…</p>';
  const lines = document.getElementById('ledger').value.split(/\\n+/).map(s=>s.trim()).filter(Boolean);
  const res = await fetch('/api/tools/liability-preview',{method:'POST',headers:{'Content-Type':'application/json'},
    body: JSON.stringify({lines, year: +document.getElementById('year').value,
      certificate_price_eur: parseFloat(document.getElementById('price').value)||null,
      default_origin: document.getElementById('origin').value||'IN'})}).then(r=>r.json());
  let h = '<table><tr><th>Line</th><th>CN</th><th>Outcome</th><th>tCO₂e</th><th>Certs</th><th>Est. cost</th><th>Basis</th></tr>';
  res.lines.forEach((l,i)=>{ h += `<tr><td>${i+1}</td><td class="mono">${l.cn_code}</td>
    <td><span class="pill ${l.outcome==='PRICED'?'ok':(l.outcome==='OUT_OF_SCOPE'?'':'warn')}">${l.outcome}</span></td>
    <td>${l.embedded_emissions_tco2e ?? '-'}</td><td>${l.certificates ?? '-'}</td><td>${l.estimated_cost_eur!=null?'€'+l.estimated_cost_eur.toLocaleString():'-'}</td>
    <td class="mono">${l.basis}</td></tr>`; });
  h += `</table><p style="padding:14px 18px"><b>Total certificates ≈ ${res.totals.certificates}</b> · <b>est. cost ≈ €${res.totals.estimated_cost_eur?.toLocaleString() ?? '-'}</b> (${res.totals.price_label})<br><span class="meta">TABLES: ${res.totals.dataset_versions} · ${res.totals.guardrail}</span></p>`;
  out.innerHTML = h;
};\n</script>'''
    return ("CBAM liability preview - EuroSetu", "Price EU-bound shipment lines on official CBAM defaults and benchmarks.", body, extra)


def threshold_page() -> tuple[str, str]:
    body = hero("TOOLS · CBAM WEDGE", "CBAM threshold checker",
        "Three questions, instant read: does the EU 50-tonne test catch you - and what about the UK £50,000 test if you ship there too?")
    body += '''<section class="form-card"><h2>Your position</h2>
<label for="mass">EU-bound CBAM-goods mass this calendar year (tonnes, per importer entity)</label>
<input id="mass" inputmode="decimal" placeholder="e.g. 42">
<label for="ukval">UK-bound CBAM-goods customs value, rolling 12 months (£, if applicable)</label>
<input id="ukval" inputmode="decimal" placeholder="e.g. 38000">
<button class="btn" id="run">Check my position →</button>
<div class="result" id="out" style="display:none"></div>
<p class="meta" style="margin-top:14px">BROWSER-ONLY. NOTHING YOU TYPE LEAVES THIS PAGE.</p></section>
<section class="faq"><h2>The rules behind the read</h2>
<details><summary>EU: the 50-tonne test</summary><p>Per importer of record, per calendar year, mass of CBAM goods released for free circulation. Above 50 t: authorised CBAM declarant status + verified embedded emissions. Scrap and out-of-scope codes don't count; downstream in-scope products (fasteners 7318, structures 7308, tube 7304-7306) do. <a href="/guides/cbam-50t-threshold">Full guide →</a></p></details>
<details><summary>UK: the £50,000 test (for reference)</summary><p>UK CBAM (Finance Act 2026, from 1 Jan 2027) registers at £50,000 of CBAM-goods customs value in a rolling 12 months (or £50,000 expected in the next 30 days). Different instrument, different threshold - same evidence discipline.</p></details>
</section>'''
    body += _rules_footer()
    extra = '''<script>
document.getElementById('run').onclick = async () => {
  const out = document.getElementById('out'); out.style.display='block';
  const res = await fetch('/api/tools/threshold',{method:'POST',headers:{'Content-Type':'application/json'},
    body: JSON.stringify({mass_t: parseFloat(document.getElementById('mass').value)||0,
      uk_value_gbp: parseFloat(document.getElementById('ukval').value)||null})}).then(r=>r.json());
  out.innerHTML = `<p style="padding:16px 18px"><span class="pill ${res.eu.in_scope?'bad':'ok'}">${res.eu.verdict}</span> ${res.eu.detail}<br><br><span class="pill">${res.uk.verdict}</span> ${res.uk.detail}</p>`;
};\n</script>'''
    return ("CBAM threshold checker - EuroSetu", "EU 50-tonne and UK £50,000 CBAM threshold instant read.", body, extra)


def relief_page() -> tuple[str, str]:
    schemes = "".join(f"<li>{s}</li>" for s in CARBON_SCHEMES)
    body = hero("TOOLS · CBAM WEDGE", "Carbon price relief: what counts toward CBAM credit",
        "Article 9 reduces your surrender for carbon prices effectively paid abroad - as converted certificates with evidence, never as a raw currency guess.")
    body += f'''<section><h2>How the deduction works</h2>
<p>Gross certificates − free-allocation adjustment − <b>converted carbon-price reduction</b> = net surrender. The reduction is a number of certificates derived under the implementing methodology from the <b>effective</b> price (net of free allocation, rebates, refunds) on the same emissions - capped at the liability, never negative.</p>
<p><b>Worked illustration:</b> 100 t steel at 2.0 tCO₂e/t = 200 tCO₂e. At labelled scenario €85/tCO₂e → €17,000 gross. Evidenced effective price of €20/tCO₂e converts to ≈200 certificates ≈ €4,000 off → net ≈ €13,000.</p></section>
<section class="form-card"><h2>Estimate your reduction</h2>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
<div><label for="emb">Embedded emissions (tCO₂e)</label><input id="emb" value="200" inputmode="decimal"></div>
<div><label for="price">Certificate price €/tCO₂e</label><input id="price" value="85" inputmode="decimal"></div>
<div><label for="red">Converted reduction (certificates, evidenced)</label><input id="red" value="40" inputmode="decimal"></div>
<div><label for="faa">Free-allocation adjustment (tCO₂e)</label><input id="faa" value="0" inputmode="decimal"></div>
</div><button class="btn" id="run">Estimate net surrender →</button>
<div class="result" id="out" style="display:none"></div></section>
<section><h2>Schemes importers ask about most</h2><p>Qualification is per-consignment evidence, not list membership - but these are the schemes behind most relief questions:</p><ol>{schemes}</ol></section>
<section><h2>The evidence kit</h2><ol><li><b>Scheme + installation statement</b> - which pricing scheme, which installation, which emissions.</li><li><b>Effective price proof</b> - price actually paid per tCO₂e after free allocation/rebates.</li><li><b>Independent verification</b> - verifier statement, not a supplier invoice alone.</li><li><b>Converted certificate figure</b> - the legally converted reduction entered per line.</li></ol>
<p><a href="/guides/carbon-price-relief">Full guide →</a></p></section>'''
    body += _rules_footer()
    extra = '''<script>
document.getElementById('run').onclick = async () => {
  const out = document.getElementById('out'); out.style.display='block';
  const g = id => parseFloat(document.getElementById(id).value)||0;
  const res = await fetch('/api/tools/relief-estimate',{method:'POST',headers:{'Content-Type':'application/json'},
    body: JSON.stringify({embedded_tco2e: g('emb'), certificate_price_eur: g('price'), reduction_certificates: g('red'), faa_tco2e: g('faa')})}).then(r=>r.json());
  out.innerHTML = `<p style="padding:16px 18px">Gross <b>€${res.gross_cost.toLocaleString()}</b> → net surrender <b>${res.net_certificates} certificates ≈ €${res.net_cost.toLocaleString()}</b><br><span class="meta">${res.note}</span></p>`;
};\n</script>'''
    return ("Carbon price relief - EuroSetu", "Article 9 CBAM deduction mechanics, evidence kit and estimator.", body, extra)


def rate_page() -> tuple[str, str]:
    rows = "".join(f"<tr><td>{y}</td><td>{f}</td><td>{'1.0 (official table)'}</td></tr>" for y, f in sorted(CBAM_FACTOR_TABLE.items()))
    body = hero("TOOLS · CBAM WEDGE", "CBAM rate watch",
        "There is no single CBAM price - certificates track EU ETS auction averages. Here's how the price works and what to budget.")
    body += f'''<section><h2>How the price works</h2>
<p>CBAM certificates are priced off the <b>weekly average EU ETS auction clearing price</b> (Implementing Regulation 2025/2548). The surrender each year is valued at quarterly average prices. EuroSetu never hardcodes a price - every illustration labels its snapshot and every API call requires one.</p>
<p><b>Current budgeting reference:</b> {SCENARIO_PRICE_LABEL}</p></section>
<section><h2>Free-allocation phase-down (moves your net every year)</h2>
<div class="result"><table><tr><th>Year</th><th>CBAM factor</th><th>CSCF</th></tr>{rows}</table></div>
<p>Net certificates per tonne ≈ specific embedded emissions − (benchmark × factor × CSCF). As the factor falls, verified intensity matters more each year.</p></section>
<section><h2>Budget rule of thumb</h2><p>Rank lines by mass × default intensity (the <a href="/liability-preview">preview</a> does this), budget the top of the list at your price snapshot, and re-run quarterly - price, factor and quota all move.</p></section>'''
    body += _rules_footer()
    return ("CBAM rate watch - EuroSetu", "How the CBAM certificate price works and what to budget.", body)


def guides_index_page() -> tuple[str, str]:
    cards = "".join(
        f'''<article class="guide-card"><p class="meta">{g["date"]} · {g["read"]} · REVIEWED {REVIEWED}</p>
<h3><a href="/guides/{g["slug"]}">{g["title"]}</a></h3><p>{g["summary"]}</p></article>'''
        for g in GUIDES)
    body = hero("GUIDES", "Market-access guides, in plain English - CBAM wedge live",
        "CBAM is the first live module, so the first nine guides go deep on it. Every guide states its rules basis and review date. Written for the ops manager, the finance owner and the supplier - not just the sustainability team. TARIC, quota, origin and sanctions guides ship with those modules.")
    body += f'<section class="guide-list">{cards}</section>'
    body += '''<section><h2>Free downloads</h2><p><a href="/supplier-data-template">Supplier emissions data template →</a> · <a href="/worked-example">Worked example: six consignments →</a></p></section>'''
    body += _rules_footer()
    return ("Market-access guides - EuroSetu (CBAM wedge live)", "Plain-English EU market-access guides: CBAM live, with rules basis and review dates.", body)


def guide_page(slug: str) -> tuple[str, str] | None:
    g = GUIDE_INDEX.get(slug)
    if not g:
        return None
    others = "".join(
        f'''<article class="guide-card"><p class="meta">{o["date"]} · {o["read"]}</p><h3><a href="/guides/{o["slug"]}">{o["title"]}</a></h3><p>{o["summary"]}</p></article>'''
        for o in GUIDES if o["slug"] != slug)[:3]
    body = f'''<section class="hero"><p class="eyebrow">GUIDE · {g["date"]} · {g["read"]}</p><h1>{g["title"]}</h1>
<p class="hero-copy">{g["summary"]}</p><p class="meta">RULES BASIS: {RULES_BASIS} · REVIEWED {REVIEWED}</p></section>
<section class="guide-card">{g["body"]}</section>
<section><h2>Keep reading</h2><div class="guide-list">{others}</div></section>'''
    body += _cta_row() + _rules_footer()
    return (g["title"] + " - EuroSetu", g["summary"], body)


def worked_example_page() -> tuple[str, str]:
    rows = "".join(
        f"<tr><td class='mono'>{l['mrn']}</td><td>{l['date']}</td><td class='mono'>{l['cn']}</td><td>{l['desc']}</td><td>{l['mass_t']}</td><td>€{l['value']:,}</td><td>{l['supplier']}</td><td>{l['file']}</td></tr>"
        for l in WORKED_LEDGER)
    body = hero("WORKED EXAMPLE | CBAM PATH", "Six consignments through the control plane",
        "A mid-size EU importer of Indian steel and aluminium, 80.2 t of CBAM goods across six consignments, run through the EuroSetu rails: compile obligations, trace evidence, price per line, prioritise by money. Tidy supplier files price cleanly; messy ones come back as fix notes; scrap stays out.")
    body += f'''<section><h2>The ledger</h2><div class="result"><table>
<tr><th>Consignment</th><th>Date</th><th>CN</th><th>Goods</th><th>Mass (t)</th><th>Value</th><th>Supplier</th><th>Evidence</th></tr>{rows}</table></div></section>
<section><h2>Line outcomes</h2><div class="result"><table>
<tr><th>Line</th><th>Outcome</th><th>Basis</th><th>Note</th></tr>
<tr><td class="mono">MRN-001 · HRC 24 t</td><td><span class="pill ok">PRICED</span></td><td class="mono">default 4.708 − FAA 1.03 = 111.96 certs ≈ €9,517</td><td>Anhui-style tidy template: monitoring ref, route (C), verifier statement. Cheapest steel line in the book.</td></tr>
<tr><td class="mono">MRN-002 · Bolts 3.2 t</td><td><span class="pill ok">PRICED</span></td><td class="mono">default 6.292, no benchmark = 20.13 certs ≈ €1,711</td><td>Same declaration covers the precursor - one-way character respected. No benchmark row exists for 7318 15, so no FAA applies.</td></tr>
<tr><td class="mono">MRN-003 · Alu 18 t</td><td><span class="pill warn">PENDING</span></td><td class="mono">default 2.057, no benchmark = 37.03 certs ≈ €3,147</td><td>Baotou-style messy file: no monitoring period, no route, unverified. Priced on the marked-up default until fixed - the most expensive line per tonne.</td></tr>
<tr><td class="mono">MRN-004 · Alu scrap 12 t</td><td><span class="pill">OUT_OF_SCOPE</span></td><td class="mono">not CBAM goods</td><td>Flagged, not priced, excluded from the 50 t test.</td></tr>
<tr><td class="mono">MRN-005 · Fe scrap 5 t</td><td><span class="pill">OUT_OF_SCOPE</span></td><td class="mono">explicit exclusion</td><td>Flagged, not priced.</td></tr>
<tr><td class="mono">MRN-006 · Clinker 30 t</td><td><span class="pill warn">PENDING</span></td><td class="mono">default 1.551 − FAA 19.48 = 27.05 certs ≈ €2,299</td><td>Covered goods, no supplier data yet - child-row default (2523 10 00 10, route B) applies at declaration unless the supplier responds.</td></tr>
</table></div>
<p><b>Totals:</b> 75.2 t in-scope mass → authorised-declarant territory from March. Priced lines total ≈ 196 certs (≈ €16,674 at the labelled €85 scenario); the two pending lines (alu + clinker, ≈ 64 certs) dominate the improvable cost - exactly where the supplier chase goes first.</p></section>
<section><h2>Tidy vs messy supplier files</h2><p><b>Tidy (Anhui-style):</b> one installation, one route, calendar-year activity, precursor table, monitoring-plan ref, verifier statement - parses with provenance, prices immediately.</p>
<p><b>Messy (Baotou-style):</b> merged cells, mixed units, no monitoring period, screenshots of spreadsheets - returned as plain-English fix notes, priced on defaults meanwhile.</p></section>'''
    body += _cta_row() + _rules_footer()
    return ("Worked example - EuroSetu", "Six consignments through the CBAM return: priced, pending and out-of-scope.", body)


def supplier_template_page() -> tuple[str, str]:
    body = hero("DOWNLOAD · CBAM WEDGE", "Supplier emissions data template",
        "The exact CBAM ask, in the exact shape the engine parses  -  and the first evidence type on the EuroSetu evidence graph. Send it to every installation behind your EU-bound goods.")
    body += '''<section class="form-card"><h2>What's inside</h2>
<ul><li>Installation + production route + monitoring period (calendar year)</li><li>Activity level (tonnes) per route</li><li>Direct emission sources with factors, oxidation, conversion</li><li>Precursor table: quantities × specific embedded emissions × value type</li><li>Monitoring-plan reference + verifier statement slot</li></ul>
<p><a class="btn" href="/api/tools/supplier-template.csv">Download CSV template →</a></p>
<p class="meta">FREE. NO SIGN-UP. PARSES DIRECTLY INTO THE LIABILITY PREVIEW FORMAT.</p></section>
<section><h2>The email to send with it</h2><pre class="template">Subject: CBAM emissions data for EU exports - one template, keeps your goods competitive\n\nHi [name],\n\nFrom January 2026 our EU imports carry CBAM certificates on embedded emissions.\nWithout your installation data we must use official defaults (+10% markup),\nwhich raises the landed cost of your goods specifically.\n\nPlease complete the attached template (one row per installation/route) and\nconfirm whether an accredited verifier can verify it - we can suggest one.\n\nThanks,\n[you]</pre></section>'''
    body += _rules_footer()
    return ("Supplier data template - EuroSetu", "Free CBAM supplier emissions data template and email.", body)


def security_page() -> tuple[str, str]:
    body = hero("SECURITY", "Security and trust",
        "Least-privilege access, checksummed evidence, full audit trails. Engineering assurance infrastructure - not legal advice or verifier accreditation.")
    body += '''<section><div class="tool-grid">
<article><h3>🔐 Access control</h3><p>Owner, ops, finance and read-only auditor roles. Supplier portal links are scoped to a single evidence request and expire. Per-request tokens; no shared logins.</p></article>
<article><h3>🔏 Evidence integrity</h3><p>Every document stored with a SHA-256 checksum against its supplier line. Re-keying is eliminated - files parse with provenance (sheet, cell, heading).</p></article>
<article><h3>📜 Audit trail</h3><p>Every save, upload, calculation and export logged with actor and timestamp. Declaration packs export the trail alongside the figures.</p></article>
<article><h3>🗄️ Retention</h3><p>Six-year retention horizon on market-access records (CBAM, customs, origin, sanctions evidence) from day one. Preview tools process in-session and store nothing.</p></article>
</div></section>'''
    body += _rules_footer()
    return ("Security - EuroSetu", "Access control, evidence integrity, audit trails and retention.", body)


def legal_page(kind: str) -> tuple[str, str]:
    if kind == "privacy":
        t = ("Privacy - EuroSetu", "How EuroSetu handles personal and shipment data.",
             hero("LEGAL", "Privacy notice", "Preview tools run in-session and store nothing. Demo and pilot data is handled under contract.") +
             "<section><p>Contact forms collect name, work email, company and message to respond to enquiries. Demo workspaces hold shipment and evidence data provided by the customer under the pilot agreement. We never sell personal data. Data requests: " + CONTACT_EMAIL + ".</p></section>" + _rules_footer())
    elif kind == "dpa":
        t = ("Data processing - EuroSetu", "How EuroSetu processes customer data as processor.",
             hero("LEGAL", "Data processing", "EuroSetu processes shipment and evidence data as processor under the pilot or production agreement. Preview tools store nothing.") +
             "<section><h2>Processor commitments</h2><ul><li>Process only on documented customer instructions (the agreement plus workspace configuration).</li><li>Limit access to named personnel on least-privilege roles; supplier links are scoped to a single evidence request and expire.</li><li>Store every document with a SHA-256 checksum; keep a six-year retention horizon on market-access records unless the agreement says otherwise.</li><li>Log every save, upload, calculation and export with actor and timestamp; export the log with the declaration pack.</li><li>Assist with data-subject requests and breach notification; sub-processors (hosting, email delivery) listed in the agreement.</li><li>Delete or return workspace data at agreement end, keeping only what law requires.</li></ul><p>Questions: " + CONTACT_EMAIL + ".</p></section>" + _rules_footer())
    else:
        t = ("Terms - EuroSetu", "Terms of use for EuroSetu tools and platform.",
             hero("LEGAL", "Terms of use", "Tools provide estimates on versioned public tables; they are not legal, customs or verification advice.") +
             "<section><p>Liability previews, threshold checks and relief estimates are planning aids computed on versioned EU reference tables with caller-supplied price snapshots. Registry surrender, customs acceptance and verifier decisions remain external. Platform use is governed by the pilot/production agreement.</p></section>" + _rules_footer())
    return t


def faq_page() -> tuple[str, str]:
    from .content_hub import SECTORS
    sectors = ", ".join(n.lower() for n, _, _ in SECTORS)
    body = hero("FAQ", "Questions importers and brokers ask",
        "Short answers with sources. Longer explainers live in the guides; numbers always trace to versioned EU tables.")
    body += f'''<section class="faq"><h2>CBAM basics</h2>
<details><summary>Is EU CBAM definitely happening?</summary><p>Yes. Regulation (EU) 2023/956 applies with the definitive regime from 1 January 2026. Transitional quarterly reporting ran 2023 to 2025 with no certificates; from 2026 importers surrender CBAM certificates against verified embedded emissions. Methodology: 2025/2547. Benchmarks: 2025/2620. Defaults: 2025/2621 corrected by 2026/1740. Verification: 2025/2546 plus 2025/2551. <a href="/guides/eu-cbam-complete-guide">Complete guide.</a></p></details>
<details><summary>Who has to act?</summary><p>The EU importer of record for CBAM goods released for free circulation, above 50 tonnes per importer per calendar year. Past that line: authorised CBAM declarant status plus verified embedded emissions. <a href="/threshold-checker">Check your position.</a></p></details>
<details><summary>What goods are caught?</summary><p>{sectors}. Scrap and listed ferro-alloys are out; downstream steel and aluminium products (fasteners 7318, structures 7308/7610, tube 7304-7306) are in. <a href="/sectors">Covered sectors.</a></p></details>
<details><summary>What do we do during 2026?</summary><p>Collect calendar-2026 installation data while you ship: activity levels, emission sources, precursors, monitoring-plan refs, verifier engagement. A declaration filed on defaults cannot later be reopened with actual data for the same period. <a href="/supplier-data-template">Supplier template.</a></p></details>
<details><summary>We already handle EU CBAM. Is UK CBAM the same?</summary><p>No. The UK scheme (Finance Act 2026, from 1 January 2027) is a tax-style charge with a GBP 50,000 rolling-12-month registration test, first return and payment 31 May 2028. Data discipline converges; instruments differ. <a href="/guides/uk-vs-eu-cbam">Side by side.</a></p></details>
<details><summary>What if suppliers will not share data?</summary><p>Then the line prices on official defaults plus statutory markup (10 percent in 2026, 20 percent in 2027, 30 percent after). Rank suppliers by mass times default intensity and chase the top first; the preview does the ranking. <a href="/liability-preview">Run the preview.</a></p></details>
<h2>Product and trust</h2>
<details><summary>Is EuroSetu only a CBAM calculator?</summary><p>No. CBAM is the live wedge module. The control plane also compiles TARIC duty, steel safeguard quota, origin, sanctions and evidence per shipment. <a href="/product">Product.</a></p></details>
<details><summary>What does EuroSetu save?</summary><p>Public preview calculations do not create a customer dossier. In an authenticated pilot, uploaded documents, extracted fields, evidence links, reviews and release decisions are recorded in the tenant workspace. Ask us to agree retention and access terms before uploading client files. <a href="/workflow">See the workflow.</a></p></details>
<details><summary>Who can see a pilot dossier?</summary><p>The hosted dossier API requires tenant-scoped bearer authentication and role checks. Customer access, retention and any identity-provider integration are agreed for each pilot; do not assume the public preview provides a production account. <a href="/security">Security.</a></p></details>
<details><summary>Can EuroSetu tell me which EU rule changed for my steel codes?</summary><p>The pilot change feed can watch eight-digit CN codes and origin countries. For supported TARIC measure rows, it records the changed row, effective date, source URL and old/new snapshot hashes. Other source updates are not presented as product-level changes until a dataset-specific comparison is validated.</p></details>
<details><summary>Does a change alert mean my shipment is non-compliant?</summary><p>No. It asks for review. A CN and origin match alone cannot prove customs treatment: measure conditions, additional codes, documents, date of import and quota availability may change the answer. EuroSetu keeps the source and row trace so a reviewer can resolve it.</p></details>
<details><summary>How do you link an invoice, packing list and mill certificate?</summary><p>The pilot dossier extracts candidate identifiers, weights and values from PDF, CSV and spreadsheets, then links evidence using those fields and source locations. Conflicts and missing links remain blocked for human review. A readable PDF is not treated as proof that its fields agree with another document.</p></details>
<details><summary>Can I correct an extracted field or broken evidence link?</summary><p>Yes. The authenticated dossier workflow records review and remediation decisions. The release result must be recalculated against the corrected evidence; an unreviewed model suggestion cannot make a shipment READY.</p></details>
<details><summary>What is available to buy today?</summary><p>EuroSetu offers scoped, human-reviewed diagnostics and design-partner pilots. A recurring self-service subscription and a guaranteed regulatory alert SLA remain subject to production acceptance and a tested refresh process. <a href="/pricing">Pricing and pilot scope.</a></p></details>
<details><summary>Is this legal or tax advice?</summary><p>No. EuroSetu is engineering assurance infrastructure, not legal advice, customs authority acceptance or verifier accreditation. Registry surrender, customs acceptance and verifier decisions remain external.</p></details>
</section>'''
    body += _cta_row() + _rules_footer()
    return ("FAQ - EuroSetu", "EU CBAM and EuroSetu questions with sources: scope, thresholds, suppliers, product, accounts.", body)


def sectors_page() -> tuple[str, str]:
    from .content_hub import SECTORS
    cards = "".join(f"<article><h3>{n}</h3><p><b>{c}</b></p><p>{d}</p></article>" for n, c, d in SECTORS)
    body = hero("COVERED SECTORS", "Which goods CBAM catches",
        "Six sectors per Annex I of Regulation (EU) 2023/956. Edges checked per consignment on versioned tables; scrap stays out.")
    body += f'<section><div class="tool-grid">{cards}</div></section>'
    body += '''<section><h2>Not sure about a code?</h2><p>Paste it into the <a href="/liability-preview">liability preview</a>: in-scope lines price on checked-in defaults, scrap and non-CBAM chapters flag OUT_OF_SCOPE, missing rows block with DEFAULT_NOT_FOUND instead of guessing.</p></section>'''
    body += _cta_row() + _rules_footer()
    return ("Covered sectors - EuroSetu", "Iron and steel, aluminium, cement, fertilisers, hydrogen, electricity: CBAM scope per Annex I.", body)


def account_page() -> tuple[str, str]:
    body = hero("ACCOUNT", "Your ledgers, saved and statement-ready",
        "Preview tools run in session and store nothing. Accounts keep every ledger, retest thresholds monthly, and export everything as one zip.")
    body += '''<section><div class="tool-grid">
<article><h3>Saved ledgers</h3><p>Every import ledger you price is kept per workspace with its year, price snapshot, dataset versions and line outcomes (PRICED, PENDING, OUT_OF_SCOPE, BLOCKED). Re-run on new tables without retyping.</p></article>
<article><h3>Monthly threshold statement</h3><p>Ledgers retest against the 50 t per-importer per-calendar-year test on every import. At 80 percent you get an early warning; crossing the line flags authorised-declarant coverage before the next shipment.</p></article>
<article><h3>Supplier portal</h3><p>Each supplier gets a scoped link: one installation, one monitoring period, one evidence type. Files land checksummed (SHA-256) against the line; messy files return as plain-English fix notes.</p></article>
<article><h3>Records vault</h3><p>Declarations, mill certs, supplier statements, monitoring-plan refs and verification reports filed per line with checksums and a completeness view. Six-year retention horizon from day one.</p></article>
<article><h3>Audit log</h3><p>Every sign-in, save, upload, calculation, role change and export written to an append-only log the workspace can read. Declaration packs export the trail alongside the figures.</p></article>
<article><h3>Export any day</h3><p>The whole workspace as one zip: ledgers, reports, documents with checksums, members and audit log. No lock-in. Your declarant, verifier and auditor get the same pack.</p></article>
</div></section>
<section><h2>Roles</h2><p>Owner, ops, finance and read-only auditor roles. Brokers run each client as its own workspace and switch between them. Supplier links never see the rest of the workspace.</p></section>
<section><h2>Start free</h2><p>Founding access: the tools above on your real data, saved ledgers and a monthly threshold statement, free through the pilot window. Prefer to watch first? Join the waitlist for the <a href="/supplier-data-template">supplier template</a> and plain-English alerts when the rules move.</p><p><a class="btn" href="/demo">Request demo access</a> <a class="btn" href="/liability-preview" style="margin-left:10px">Try the preview first</a></p></section>'''
    body += _rules_footer()
    return ("Account - EuroSetu", "Saved ledgers, monthly threshold statements, supplier portal, vault, audit log and one-zip export.", body)


def changelog_page() -> tuple[str, str]:
    body = hero("CHANGELOG", "Rules changelog",
        "Every rule change that moves a number, with the table version behind it. Reviewed 2026-10-02.")
    body += '''<section><div class="result"><table>
<tr><th>Date</th><th>Change</th><th>Effect</th></tr>
<tr><td>2026-10-02</td><td>Rules basis review</td><td>Confirmed 2023/956 plus 2025/2547, 2025/2620, 2025/2621 corrected by 2026/1740, 2025/2546 plus 2025/2551; steel 2026/1384 plus 2026/1457. No figure changes.</td></tr>
<tr><td>2026-07-31</td><td>Defaults correction 2026/1740</td><td>Default table values corrected; certificate defaults recomputed with statutory markup. Ledgers priced before this date show the prior dataset version.</td></tr>
<tr><td>2026-07-01</td><td>Steel safeguard snapshot 2026/1457</td><td>Quota categories and balances apply through 31 Dec 2026; out-of-quota duty stacks with CBAM per tonne.</td></tr>
<tr><td>2026-01-01</td><td>CBAM definitive regime starts</td><td>Certificates accrue on CBAM imports; 2026 is the first monitoring year for the 2027 declaration cycle.</td></tr>
<tr><td>2025-12-22</td><td>Methodology, benchmarks, verification published</td><td>2025/2547 (method), 2025/2620 (benchmarks and FAA), 2025/2546 plus 2025/2551 (verification) checked into versioned tables.</td></tr>
</table></div><p>Each liability preview response stamps its dataset versions so a saved ledger always shows which tables priced it.</p></section>'''
    body += _cta_row() + _rules_footer()
    return ("Rules changelog - EuroSetu", "EU CBAM and steel rule changes with dataset versions.", body)


# ---------------------------------------------------------------- tool APIs

def api_liability_preview(payload: dict) -> dict:
    from .cbam_definitive_v2 import select_default, free_allocation_adjustment, certificate_obligation
    # Scope gate is multi-sector: the checked-in default table covers cement (25),
    # ores/slag (26), inorganic chemicals incl. hydrogen (28), fertilisers (31),
    # iron & steel (72-73) and aluminium (76). Scrap and ferro-alloy exclusions
    # are flagged out-of-scope; anything outside CBAM chapters is out-of-scope.
    _SCRAP = ("7204", "7602", "72022", "72023000", "72025000", "72027000",
              "72028000", "72029100", "72029200", "72029300", "720299")
    _CHAPTERS = ("25", "26", "28", "31", "72", "73", "76", "2716", "2804")
    raw = payload.get("lines", [])
    year = int(payload.get("year") or 2026)
    price = payload.get("certificate_price_eur")
    price = None if price in (None, "") else float(price)
    default_origin = (payload.get("default_origin") or "IN").upper()
    lines: list[dict] = []
    total_certs = 0.0
    for entry in raw:
        if isinstance(entry, str):
            parts = [p.strip() for p in entry.split(",")]
            cn = "".join(ch for ch in (parts[0] if parts else "") if ch.isdigit())
            mass = float(parts[1]) if len(parts) > 1 and parts[1] else 0
            origin = (parts[3] if len(parts) > 3 and parts[3] else default_origin).upper()
        elif isinstance(entry, dict):
            cn = "".join(ch for ch in str(entry.get("cn_code", "")) if ch.isdigit())
            mass = float(entry.get("mass_t") or 0)
            origin = str(entry.get("origin_country") or default_origin).upper()
        else:
            continue
        if not cn or mass <= 0:
            continue
        if any(cn.startswith(x) for x in _SCRAP) or not cn.startswith(_CHAPTERS):
            lines.append({"cn_code": cn, "outcome": "OUT_OF_SCOPE", "basis": "not CBAM goods / excluded (scrap or non-CBAM chapter)",
                          "embedded_emissions_tco2e": 0, "certificates": 0, "estimated_cost_eur": 0})
            continue
        d = select_default(origin, cn, None, year)
        if not d["available"]:
            lines.append({"cn_code": cn, "outcome": "BLOCKED", "basis": d.get("reason", "DEFAULT_NOT_FOUND"),
                          "embedded_emissions_tco2e": None, "certificates": None, "estimated_cost_eur": None})
            continue
        faa = free_allocation_adjustment(cn, mass, year, d.get("production_route"))
        faa_adj = faa["free_allocation_adjustment_tco2e"] if faa.get("available") else 0.0
        obl = certificate_obligation(d["certificate_default_total"], mass, {"free_allocation_adjustment_tco2e": faa_adj}, price)
        certs = obl["certificates_to_surrender_estimate"]
        total_certs += certs
        lines.append({"cn_code": cn, "outcome": "PRICED", "basis": f"default {d['total']} +{int(d['markup']*100)}% = {d['certificate_default_total']} tCO₂e/t ({d['dataset_version']})",
                      "embedded_emissions_tco2e": obl["embedded_emissions_tco2e"],
                      "certificates": round(certs, 3),
                      "estimated_cost_eur": obl["estimated_certificate_cost_eur"]})
    versions = "defaults 2025/2621-corr-2026/1740 · benchmarks 2025/2620 · CSCF CELEX:32026D1862"
    return {"lines": lines,
            "totals": {"certificates": round(total_certs, 3),
                       "estimated_cost_eur": round(total_certs * price, 2) if price is not None else None,
                       "price_label": f"labelled scenario €{price}/tCO₂e" if price is not None else "no price supplied - certificates only",
                       "dataset_versions": versions,
                       "guardrail": "Estimates on versioned tables; registry surrender and authority acceptance remain external."}}


def api_threshold(payload: dict) -> dict:
    mass = float(payload.get("mass_t") or 0)
    ukv = payload.get("uk_value_gbp")
    ukv = None if ukv in (None, "") else float(ukv)
    eu = {"in_scope": mass > 50, "mass_t": mass, "threshold_t": 50}
    if mass > 50:
        eu.update({"verdict": "IN SCOPE (EU)", "detail": f"{mass:g} t exceeds the 50 t calendar-year test - authorised CBAM declarant status and verified embedded emissions required."})
    elif mass >= 40:
        eu.update({"verdict": "CLOSE - MONITOR", "detail": f"{mass:g} t is at {mass/50*100:.0f}% of the 50 t line. One more shipment can trip it mid-year - track per importer entity."})
    else:
        eu.update({"verdict": "BELOW THRESHOLD (EU)", "detail": f"{mass:g} t is below the 50 t calendar-year test. Keep tracking - the test is per importer entity, not per shipment."})
    if ukv is None:
        uk = {"verdict": "UK: NOT CHECKED", "detail": "Supply a rolling-12-month UK CBAM-goods value to test the £50,000 registration line (Finance Act 2026, from 1 Jan 2027)."}
    elif ukv >= 50000:
        uk = {"verdict": "IN SCOPE (UK)", "detail": f"£{ukv:,.0f} meets the £50,000 rolling-12-month registration test - UK CBAM registration and quarterly accounting apply."}
    else:
        uk = {"verdict": "BELOW THRESHOLD (UK)", "detail": f"£{ukv:,.0f} is below £50,000. Watch the 30-day-forward test: expecting to hit £50k in the next 30 days also triggers registration."}
    return {"eu": eu, "uk": uk}


def api_relief_estimate(payload: dict) -> dict:
    emb = float(payload.get("embedded_tco2e") or 0)
    price = float(payload.get("certificate_price_eur") or SCENARIO_PRICE_EUR)
    red = max(0.0, float(payload.get("reduction_certificates") or 0))
    faa = max(0.0, float(payload.get("faa_tco2e") or 0))
    net = max(0.0, emb - faa - red)
    return {"gross_cost": round(emb * price, 2), "net_certificates": round(net, 3),
            "net_cost": round(net * price, 2),
            "note": "Reduction accepted only as converted certificates with evidence (Art. 9). Raw currency values are never converted heuristically."}


SUPPLIER_CSV = ("installation_name,production_route,monitoring_period,cn_code,activity_level_t,"
    "direct_emissions_tco2,precursor_qty_t,precursor_see_tco2e_per_t,precursor_value_type,"
    "monitoring_plan_ref,verification_status,notes\n"
    '"Example Works 1",(C),2026,72083900,24000,45600,1200,1.85,ACTUAL,MP-2026-001,VERIFIED,"\n')


# ---------------------------------------------------------------- workflow-run tool

def workflow_run_page() -> tuple[str, str]:
    body = hero("TOOLS · WORKFLOW RUN", "Run the workflow on your documents",
        "Upload PDFs, CSVs, Excel workbooks or text files - or paste a CSV ledger. EuroSetu parses them in-session (nothing stored), maps each document to its workflow step, and runs the real evidence → decision → compiler → entitlement engines. Fail-closed throughout: missing data blocks with a named code, never a guess.")
    body += '''<section><p class="meta"><b>PILOT REVIEW:</b> PDF observations and document links are candidates. This page does not issue customs or CBAM release decisions for uploaded PDFs.</p></section><section class="form-card"><h2>1 · Add documents</h2>
<p class="meta">PDF · CSV · XLSX/XLS · TXT · UP TO 8 MB PER FILE · PROCESSED IN-SESSION, NOTHING STORED</p>
<label for="files">Upload files</label>
<input id="files" type="file" multiple accept=".pdf,.csv,.xlsx,.xls,.txt">
<label for="paste">Or paste a CSV ledger (same shape as the <a href="/api/tools/supplier-template.csv">supplier template</a> or the diagnostic: transaction_id,po_number,cn_code,origin,destination,shipment_date,quantity_t,line_value_eur)</label>
<textarea id="paste" placeholder="transaction_id,po_number,cn_code,origin,destination,shipment_date,quantity_t,line_value_eur&#10;TX-001,PO-1,72221119,IN,DE,2026-09-29,24.371,47823.69"></textarea>
<label style="font-weight:400"><input type="checkbox" id="compare-ocr" style="width:auto"> Compare image OCR (Tesseract, first 3 pages; review-only)</label>
<label for="docurl">Or a hosted document URL (firecrawl comparison path - needs FIRECRAWL_API_KEY on the server)</label>
<input id="docurl" placeholder="https://example.com/supplier-emissions.pdf">
<div style="margin:14px 0;padding:14px;border:1px solid #d7e2e7;border-radius:8px">
<label style="font-weight:400"><input type="checkbox" id="use-llm" style="width:auto"> Use a model to propose PDF fields (pilot access required)</label>
<label for="model-id">OpenAI-compatible model ID</label>
<input id="model-id" value="deepseek/deepseek-v4-flash" autocomplete="off">
<p class="meta">PDF text is sent to the configured model gateway. The gateway URL and API key stay on the server. Model fields must cite exact PDF lines and remain blocked until reviewed. CSV/XLSX use deterministic parsing.</p>
</div>
<button class="btn" id="parse">Parse documents →</button>
<div class="result" id="parseout" style="display:none"></div>
</section>
<section class="form-card"><h2>2 · Confirm lines &amp; run the workflow</h2>
<p class="meta">EDIT THE EXTRACTED CN / QTY / VALUE / DATE BEFORE COMPILING - NOTHING IS GUESSED FOR YOU</p>
<div class="result" id="linesout"><p style="padding:16px 18px" class="meta">Parse documents first - editable shipment lines appear here.</p></div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px">
<div><label for="ytd">Importer CBAM mass YTD (t, before these lines)</label><input id="ytd" value="30" inputmode="decimal"></div>
<div><label for="impdate">Default import date (YYYY-MM-DD)</label><input id="impdate" value="2026-09-29"></div>
</div>
<p style="margin-top:12px"><label style="display:inline;font-weight:400"><input type="checkbox" id="seed" style="width:auto"> Seed demo TARIC snapshot (synthetic 0% rows, as_of = import date - clearly labelled, same pattern as the redacted demo)</label><br>
<label style="display:inline;font-weight:400"><input type="checkbox" id="cbampack" style="width:auto"> Attach synthetic verified CBAM pack (demo only - real runs need the supplier's monitoring plan + verifier statement)</label><br>
<label style="display:inline;font-weight:400"><input type="checkbox" id="declarant" checked style="width:auto"> Authorised CBAM declarant confirmed</label>
<label style="display:inline;font-weight:400;margin-left:14px"><input type="checkbox" id="emiv" style="width:auto"> CBAM emissions verified / lawful-default treatment</label></p>
<button class="btn" id="compile">Run workflow →</button>
<div class="result" id="compileout" style="display:none"></div>
</section>
<section><h2>What each document contributes</h2><div class="tool-grid">
<article><h3>🧭 Step 1 - Compile obligations</h3><p>Commercial invoices, shipping bills, packing lists, ledgers (CSV/XLSX): CN code + quantity + customs value + origin → TARIC duty scope, steel safeguard category, CBAM scope. This is where out-of-scope lines (scrap, non-CBAM chapters) are flagged.</p></article>
<article><h3>🔍 Step 2 - Trace evidence</h3><p>Mill test certificates, supplier emissions statements, verifier reports: each becomes an evidence object with a lifecycle state (VALID only when VERIFIED and fresh; otherwise UNVERIFIED / STALE / MISSING) feeding the fail-closed decision.</p></article>
<article><h3>📦 Step 3 - Price, prioritise, pack</h3><p>Resolved lines run the full compiler (customs pack + PPWR + REACH + sanctions + valuation + origin) and the active-entitlement check → READY_FOR_SUBMISSION / ENTITLED or BLOCKED with named blockers ranked by money.</p></article>
<article><h3>⚖️ Parser comparison</h3><p>PDFs compare <b>pypdf</b> and <b>pdftotext</b> text layers with optional <b>Tesseract image OCR</b> (automatic on image-only scans, review-only) and <b>PaddleOCR PP-StructureV3</b> when other paths fail - timed, with CN hits per parser; best pick = most CN hits, tie-break V3 first. Firecrawl compares on hosted URLs only. CSV/XLSX parse via <b>polars</b> with column mapping shown. The table under each file shows exactly what each parser saw.</p></article>
</div></section>'''
    body += _rules_footer()
    extra = '''<script>
let LINES = [];
let SOURCE_CONFLICTS = [];
fetch('/api/workflow-run/model-config').then(r=>r.json()).then(c=>{
  if (c.default_model) document.getElementById('model-id').value=c.default_model;
}).catch(()=>{});
const esc = s => String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;');
document.getElementById('parse').onclick = async () => {
  const out = document.getElementById('parseout'); out.style.display='block'; out.innerHTML='<p style="padding:18px">Parsing…</p>';
  const fd = new FormData();
  for (const f of document.getElementById('files').files) fd.append('files', f);
  fd.append('pasted_csv', document.getElementById('paste').value);
  fd.append('doc_url', document.getElementById('docurl').value);
  if (document.getElementById('compare-ocr').checked) fd.append('compare_ocr','true');
  const useLlm = document.getElementById('use-llm').checked;
  if (useLlm) { fd.append('use_llm','true'); fd.append('model_id',document.getElementById('model-id').value); }
  const pilotToken = localStorage.getItem('eurosetu_pilot_token') || '';
  const headers = useLlm && pilotToken ? {'Authorization':'Bearer '+pilotToken,
    'x-eurosetu-tenant':localStorage.getItem('eurosetu_pilot_tenant')||'tenant-a'} : {};
  const response = await fetch('/api/workflow-run/parse',{method:'POST',headers,body:fd});
  const res = await response.json();
  if (!response.ok) { out.innerHTML='<p style="padding:18px" class="mono">'+esc(res.detail||'Parse request failed')+'</p>'; return; }
  LINES = [];
  SOURCE_CONFLICTS = res.reconciliation?.conflicts || [];
  let h = '';
  if (SOURCE_CONFLICTS.length) h += `<p style="padding:14px 18px" class="mono"><b>BLOCKED: ${SOURCE_CONFLICTS.length} source conflict(s)</b> · ${esc(SOURCE_CONFLICTS.map(x=>x.field+': '+x.left.join('/')+' vs '+x.right.join('/')).join('; '))}. Reconcile the source documents before release.</p>`;
  if (res.reconciliation?.edges?.length) h += `<p style="padding:0 18px" class="meta">${res.reconciliation.edges.length} document link candidate(s), all requiring review.</p>`;
  res.documents.forEach((d,di)=>{
    h += `<p style="padding:14px 18px 0"><b>${esc(d.filename)}</b> <span class="pill ${d.ok?'ok':'bad'}">${d.ok?'PARSED':'BLOCKED'}</span> <span class="meta">${esc(d.kind)}${d.pii_codes&&d.pii_codes.length?' · PII REDACTED: '+d.pii_codes.join(','):''}</span></p>`;
    if (!d.ok) { h += `<p style="padding:0 18px" class="mono">${esc(d.code)} - ${esc(d.reason)}</p>`; return; }
    if (d.parser_comparison) {
      h += '<table><tr><th>Parser</th><th>Outcome</th><th>Pages/rows</th><th>Chars</th><th>Time</th><th>CN hits</th><th>Note</th></tr>';
      d.parser_comparison.forEach(p=>{ const note = !p.ok ? (p.code||'FAILED') : (p.columns?('cols: '+(p.columns||[]).join(', ')):(p.reason||''));
        // advisory = a fallback/limit note, not a failed parse. Painting it red
        // made a 348-page doc's healthy pypdf result look like an error.
        const adv = !p.ok && p.advisory;
        const lowText = p.ok && d.kind==='pdf' && (p.chars||0)<20;
        const pill = lowText ? 'warn' : (p.ok ? 'ok' : (adv ? 'warn' : 'bad'));
        const label = lowText ? 'LOW TEXT' : (p.ok ? 'OK' : (adv ? 'FALLBACK' : 'GATED'));
        h += `<tr><td class="mono">${esc(p.parser)}</td><td><span class="pill ${pill}">${label}</span></td><td>${p.pages ?? p.rows ?? '-'}</td><td>${p.chars ?? '-'}</td><td>${p.time_ms ?? '-'} ms</td><td class="mono">${(p.cns_found||[]).join(', ')||'-'}</td><td class="mono">${esc(note)}</td></tr>`; });
      h += '</table>';
    }
    if (d.selected_parser) h += `<p style="padding:0 18px" class="meta">SELECTED TEXT SOURCE: ${esc(d.selected_parser)} · OCR output requires review</p>`;
    if (d.mapped_columns) h += `<p style="padding:0 18px" class="meta">POLARS COLUMN MAP: ${esc(JSON.stringify(d.mapped_columns))}</p>`;
    const rc = d.receipts;
    if (rc && rc.rows) {
      h += `<p style="padding:0 18px" class="meta">${rc.rows} RECEIPT RECORD(S) EXTRACTED - AMOUNTS LEFT BLANK WERE AMBIGUOUS AND WERE NOT GUESSED</p>`;
      h += '<table><tr><th>Receipt</th><th>Vendor</th><th>Total (raw → parsed)</th><th>Qty (raw → parsed)</th><th>Date</th><th>Codes</th><th>Duplicate of</th></tr>';
      rc.records.forEach(r=>{ const num = (raw,val)=> val===null||val===undefined ? `<span class="mono">${esc(raw||'?')} → <b>not parsed</b></span>` : `<span class="mono">${esc(raw||'?')} → ${esc(val)}</span>`;
        h += `<tr><td class="mono">${esc(r.receipt_id||'?')}</td><td>${esc(r.vendor||'?')}</td><td>${num(r.total_raw,r.total)}</td><td>${num(r.qty_raw,r.quantity)}</td><td class="mono">${esc(r.date||'-')}</td><td class="mono">${esc((r.codes||[]).join(', ')||'OK')}</td><td class="mono">${esc(r.duplicate_of||'-')}</td></tr>`; });
      h += '</table>';
    }
    if (d.ocr_review) {
      const o=d.ocr_review;
      h += `<details style="margin:0 18px 8px"><summary>IMAGE OCR · ${esc(o.code||((o.pages||[]).length+' page(s)'))} · ${esc(o.processing_time_ms??'?')} ms · review-only</summary>`;
      (o.pages||[]).forEach(p=>{h += `<p class="meta">Page ${p.page} · confidence ${esc(p.mean_confidence??'?')}</p><pre class="mono" style="white-space:pre-wrap">${esc((p.lines||[]).map(l=>l.text+'  [box '+l.bbox.join(', ')+']').join('\\n'))}</pre>`;});
      h += '</details>';
    }
    if (d.observations) {
      const o=d.observations;
      h += `<p style="padding:0 18px" class="meta">PDF OBSERVATIONS · ${o.fields.length} fields · ${o.tables.reduce((n,t)=>n+t.rows.length,0)} table rows · ${esc(o.processing_time_ms)} ms · review required</p>`;
      if (o.fields.length) {
        h += '<table><tr><th>Field</th><th>Source value</th><th>Page</th><th>Box</th></tr>';
        o.fields.forEach(f=>{h += `<tr><td>${esc(f.field)}</td><td class="mono">${esc(f.raw)}</td><td>${esc(f.page)}</td><td class="mono">${esc(f.bbox?f.bbox.join(', '):'Unavailable')}</td></tr>`;});
        h += '</table>';
      }
      o.tables.forEach(t=>{h += `<details style="margin:0 18px 8px"><summary>${esc(t.kind)} · page ${t.page} · ${t.rows.length} rows</summary><pre class="mono" style="white-space:pre-wrap">${esc(JSON.stringify(t.rows,null,2))}</pre></details>`;});
    }
    if (d.llm_proposal && !d.llm_proposal.ok) h += `<p style="padding:0 18px" class="mono">MODEL: ${esc(d.llm_proposal.code||'NO_VERIFIABLE_LINES')}</p>`;
    if (d.structured_ingestion?.issues?.length) h += `<p style="padding:0 18px" class="mono">INGEST ISSUES: ${esc(JSON.stringify(d.structured_ingestion.issues))}</p>`;
    (d.candidates||[]).forEach((c,ci)=>{
      const id = LINES.length;
      LINES.push({issues:c.issues||[],field_provenance:c.field_provenance||{},review_confirmed:false,invoice_number:c.invoice_number||'',destination_country:c.destination_country||'',shipment_ref:c.shipment_ref||`${esc(d.filename)}-${ci+1}`,cn_code:c.cn_code||'',quantity_t:c.quantity_t??'',customs_value_eur:c.customs_value_eur??'',origin_country:c.origin_country||'',import_date:c.import_date||'',evidence:[{id:`E-${di}-${ci}`,evidence_type:'COMMERCIAL_INVOICE',verified:false}],doc:di});
      h += `<p style="padding:0 18px" class="meta">CANDIDATE ${id+1}: CN <b class="mono">${esc(c.cn_code||'?')}</b> · qty ${esc(c.quantity_t??'?')} t · €${esc(c.customs_value_eur??'?')} · origin ${esc(c.origin_country||'?')} · date ${esc(c.import_date||'(default below)')}</p>`;
    });
    h += `<p style="padding:0 18px"><b>Step 1 - compile:</b> ${esc((d.steps.step_1_compile_obligations||[]).join(' · '))}<br><b>Step 2 - evidence:</b> ${esc((d.steps.step_2_trace_evidence||[]).join(' · '))}<br><b>Step 3 - pack:</b> ${esc((d.steps.step_3_price_prioritise_pack||[]).join(' · '))}</p>`;
    h += `<details style="margin:0 18px 8px"><summary class="meta">REDACTED PREVIEW</summary><p class="mono">${esc((d.redacted_preview||'').slice(0,800))}</p></details>`;
  });
  out.innerHTML = h || '<p style="padding:18px">No documents - upload a file or paste a CSV.</p>';
  renderLines();
};
function renderLines(){
  const el = document.getElementById('linesout');
  if (!LINES.length) return;
  let h = '<table><tr><th>#</th><th>Ref</th><th>Invoice</th><th>CN</th><th>Qty t</th><th>Value €</th><th>Origin</th><th>Destination</th><th>Date</th><th>Evidence verified?</th><th>Fields reviewed?</th></tr>';
  LINES.forEach((l,i)=>{ h += `<tr><td>${i+1}</td><td class="mono"><input data-i="${i}" data-k="shipment_ref" value="${esc(l.shipment_ref)}" style="width:130px"></td><td><input data-i="${i}" data-k="invoice_number" value="${esc(l.invoice_number)}" style="width:100px"></td><td><input data-i="${i}" data-k="cn_code" value="${esc(l.cn_code)}" style="width:90px"></td><td><input data-i="${i}" data-k="quantity_t" value="${esc(l.quantity_t)}" style="width:70px"></td><td><input data-i="${i}" data-k="customs_value_eur" value="${esc(l.customs_value_eur)}" style="width:90px"></td><td><input data-i="${i}" data-k="origin_country" value="${esc(l.origin_country)}" style="width:44px"></td><td><input data-i="${i}" data-k="destination_country" value="${esc(l.destination_country)}" style="width:44px"></td><td><input data-i="${i}" data-k="import_date" value="${esc(l.import_date)}" style="width:100px"></td><td><input type="checkbox" data-i="${i}" data-k="verified" ${l.evidence[0].verified?'checked':''}></td><td><input type="checkbox" data-i="${i}" data-k="review_confirmed" ${l.review_confirmed?'checked':''}></td></tr>`; });
  h += '</table>';
  el.innerHTML = h;
  el.querySelectorAll('input').forEach(inp=>{ inp.onchange = ()=>{
    const l = LINES[+inp.dataset.i];
    if (inp.dataset.k==='verified') l.evidence[0].verified = inp.checked;
    else if (inp.dataset.k==="review_confirmed") l.review_confirmed = inp.checked;
    else l[inp.dataset.k] = inp.value;
  };});
}
document.getElementById('compile').onclick = async () => {
  const out = document.getElementById('compileout'); out.style.display='block'; out.innerHTML='<p style="padding:18px">Compiling…</p>';
  const res = await fetch('/api/workflow-run/compile',{method:'POST',headers:{'Content-Type':'application/json'},
    body: JSON.stringify({lines:LINES, source_conflicts:SOURCE_CONFLICTS, importer_cbam_mass_ytd_t:parseFloat(document.getElementById('ytd').value)||0,
      seed_demo_taric:document.getElementById('seed').checked, demo_cbam_pack:document.getElementById('cbampack').checked,
      authorised_cbam_declarant:document.getElementById('declarant').checked, cbam_emissions_verified:document.getElementById('emiv').checked})}).then(r=>r.json());
  let h = '<table><tr><th>Line</th><th>Evidence</th><th>Decision</th><th>Compiler</th><th>Entitlement</th><th>Blockers</th></tr>';
  res.lines.forEach(l=>{ const pill = s => s==='READY'||s==='READY_FOR_SUBMISSION'||s==='ENTITLED'?'ok':(s==='BLOCKED'?'bad':'warn');
    h += `<tr><td class="mono">${esc(l.shipment_ref)}</td><td class="mono">${esc(JSON.stringify(l.evidence_states))}</td><td><span class="pill ${pill(l.decision)}">${esc(l.decision)}</span></td><td><span class="pill ${pill(l.compiler_decision)}">${esc(l.compiler_decision)}</span></td><td><span class="pill ${pill(l.entitlement_decision)}">${esc(l.entitlement_decision)}</span></td><td class="mono">${esc((l.blockers||[]).map(b=>b.engine+':'+(b.code||'')).join('; ')||'-')}</td></tr>`; });
  h += `</table><p style="padding:14px 18px"><span class="meta">${esc(res.note||'')}</span></p>`;
  out.innerHTML = h;
};
</script>'''
    return ("Run the workflow on your documents - EuroSetu", "Upload PDFs, CSVs, Excel or text: parse in-session, map each document to its workflow step, run the real engines.", body, extra)


def api_workflow_run_parse(files: list[tuple[str, bytes]], pasted_csv: str = "",
                           doc_url: str = "", compare_ocr: bool = False) -> dict:
    from . import document_ingest as ing
    from . import document_lines as line_ingest
    from .pdf_observations import extract_pdf_observations, invoice_candidates, reconcile_documents
    docs: list[dict] = []

    def one(filename: str, data: bytes) -> dict:
        lower = (filename or "").lower()
        if len(data) > 8 * 1024 * 1024:
            return {"filename": filename, "kind": "unknown", "ok": False,
                    "code": "FILE_TOO_LARGE",
                    "reason": "8 MB per-file limit for the in-session tool."}
        if lower.endswith(".pdf"):
            structured = line_ingest.ingest_pdf(data, filename)
            observations = extract_pdf_observations(data, filename)
            comp = ing.compare_pdf_parsers(data, include_paddle=False)
            text_ok = any(r.get("ok") and (r.get("chars") or 0) >= 20 for r in comp)
            ocr_review = None
            if compare_ocr or not text_ok:
                from .pdf_image_ocr import extract_image_ocr
                ocr = extract_image_ocr(data, filename)
                ocr_review = {"ok": ocr["ok"], "code": ocr.get("code"),
                              "processing_time_ms": ocr.get("processing_time_ms"),
                              "pages": [{"page": p["page"], "mean_confidence": p.get("mean_confidence"),
                                         "lines": p["lines"][:120]} for p in ocr.get("pages", [])]}
                comp.insert(0, {"parser": "tesseract-image-ocr", "ok": ocr["ok"],
                                "pages": ocr.get("page_count"), "chars": ocr.get("chars",0),
                                "time_ms": ocr.get("processing_time_ms"), "text": ocr.get("text", ""),
                                "code": ocr.get("code"), "cns_found": [],
                                "reason": "Raster OCR; numeric strings are not classified as CN. Review field and row joins."})
            if not any(r.get("ok") and (r.get("chars") or 0) >= 20 for r in comp):
                comp = ing.compare_pdf_parsers(data, include_paddle=True) + comp
            _prio = {"paddle-structure-v3": 3, "pypdf": 2, "pdftotext-baseline": 1,
                     "tesseract-image-ocr": 0}
            _ok = [r for r in comp if r.get("ok") and (r.get("chars") or 0) >= 20
                   and (not text_ok or r.get("parser") != "tesseract-image-ocr")]
            best = max(_ok, key=lambda r: (len(r.get("cns_found") or []),
                                           _prio.get(r.get("parser"), 0),
                                           r.get("chars", 0))) if _ok else None
            if not best:
                for r in comp:
                    r.pop("text", None)
                return {"filename": filename, "kind": "pdf", "ok": False,
                        "code": "PDF_UNPARSEABLE",
                        "reason": "; ".join(r.get("code", "?") for r in comp),
                        "parser_comparison": comp,
                        "steps": ing.map_to_steps(filename, {})}
            text = best.get("text", "")
            for r in comp:
                r.pop("text", None)
            red, pii = ing.redact_preview(text)
            ext = ing.extract_candidates(text, filename)
            if best["parser"] == "tesseract-image-ocr":
                ext["cn_codes_found"] = []
                ext["candidate"]["cn_code"] = None
            cands = structured["lines"] or invoice_candidates(observations)
            receipts = ing.extract_receipt_records(text, filename)
            return {"filename": filename, "kind": "pdf", "ok": True,
                    "selected_parser": best["parser"],
                    "observations": observations, "ocr_review": ocr_review,
                    "parser_comparison": comp, "redacted_preview": red,
                    "pii_codes": pii, "extracted": ext, "candidates": cands,
                    "receipts": receipts, "structured_ingestion": structured,
                    "steps": ing.map_to_steps(filename, ext)}
        if lower.endswith(".csv") or (pasted_csv and filename == "pasted-ledger.csv"):
            r = ing.parse_csv_polars(data)
        elif lower.endswith((".xlsx", ".xls", ".xlsm")):
            r = ing.parse_excel_polars(data)
        elif lower.endswith(".txt"):
            r = ing.parse_txt(data)
            text = r.get("text", "") if r.get("ok") else ""
            if not r.get("ok"):
                return {"filename": filename, "kind": "txt", "ok": False,
                        "code": r["code"], "reason": r["reason"],
                        "steps": ing.map_to_steps(filename, {})}
            r.pop("text", None)
            red, pii = ing.redact_preview(text)
            ext = ing.extract_candidates(text, filename)
            cands = [dict(ext["candidate"],
                           shipment_ref=f"{filename}-1")] if ext["candidate"]["cn_code"] else []
            receipts = ing.extract_receipt_records(text, filename)
            return {"filename": filename, "kind": "txt", "ok": True,
                    "parser_comparison": [{**r, "cns_found": ext["cn_codes_found"][:5]}],
                    "redacted_preview": red, "pii_codes": pii,
                    "extracted": ext, "candidates": cands,
                    "receipts": receipts, "steps": ing.map_to_steps(filename, ext)}
        else:
            return {"filename": filename, "kind": "unknown", "ok": False,
                    "code": "UNSUPPORTED_TYPE",
                    "reason": "Supported: .pdf .csv .xlsx/.xls .txt",
                    "steps": ing.map_to_steps(filename, {})}
        # The strict extractor owns decisions; polars remains an advisory comparison.
        structured = line_ingest.ingest_tabular(data, filename) if lower.endswith((".csv", ".xlsx", ".xlsm")) else {"lines": [], "issues": [{"code": "LEGACY_XLS_REQUIRES_CONVERSION"}]}
        if not r.get("ok"):
            return {"filename": filename,
                    "kind": "excel" if lower.endswith((".xlsx", ".xls", ".xlsm")) else "csv",
                    "ok": structured.get("ok", False), "code": r["code"],
                    "reason": r["reason"], "parser_comparison": [r],
                    "candidates": structured.get("lines", []),
                    "structured_ingestion": structured,
                    "steps": ing.map_to_steps(filename, {})}
        frame = r.pop("frame")
        mapped = ing.dataframe_candidates(frame, filename)
        red, pii = ing.redact_preview(r.get("text", ""))
        pseudo = {"cn_codes_found": [c["cn_code"] for c in mapped.get("candidates", []) if c.get("cn_code")][:5]}
        if not structured.get("lines"):
            return {"filename": filename,
                    "kind": "excel" if lower.endswith((".xlsx", ".xls", ".xlsm")) else "csv",
                    "ok": False, "code": "NO_USABLE_ROWS",
                    "reason": "No non-empty trade lines found - check the header row and file format.",
                    "parser_comparison": [{**r, "cns_found": []}],
                    "mapped_columns": mapped.get("mapped_columns"),
                    "steps": ing.map_to_steps(filename, {})}
        return {"filename": filename,
                "kind": "excel" if lower.endswith((".xlsx", ".xls", ".xlsm")) else "csv",
                "ok": True,
                "parser_comparison": [{**r, "cns_found": pseudo["cn_codes_found"]}],
                "mapped_columns": mapped.get("mapped_columns"),
                "redacted_preview": red, "pii_codes": pii,
                "candidates": structured.get("lines", []),
                "structured_ingestion": structured,
                "steps": ing.map_to_steps(filename, pseudo)}

    for name, data in files:
        docs.append(one(name, data))
    if (pasted_csv or "").strip():
        docs.append(one("pasted-ledger.csv", pasted_csv.encode("utf-8-sig")))
    if (doc_url or "").strip():
        from .document_ingest import parse_pdf_firecrawl_url
        r = parse_pdf_firecrawl_url(doc_url.strip())
        docs.append({"filename": doc_url.strip(), "kind": "url (firecrawl)",
                     "ok": r.get("ok", False), "code": r.get("code"),
                     "reason": r.get("reason"),
                     "parser_comparison": [{**r, "cns_found": []}],
                     "candidates": [], "steps": {"step_1_compile_obligations": [],
                     "step_2_trace_evidence": [], "step_3_price_prioritise_pack": []}})
    return {"documents": docs, "reconciliation": reconcile_documents(docs),
            "note": "Parsed in-session; nothing stored. Confirm every candidate before compiling - extraction never invents missing fields."}


def api_workflow_run_compile(payload: dict) -> dict:
    import re
    from . import decision_engine as de
    from . import eu_public_data as pub
    from . import evidence_lifecycle as ev
    from .compliance_entitlement import compile_active_entitlement
    from .market_access_compiler_v2 import compile_shipment

    def _f(v) -> float:
        try:
            return float(str(v).strip() or 0)
        except (ValueError, TypeError, AttributeError):
            return 0.0

    lines = payload.get("lines", [])
    source_conflicts = payload.get("source_conflicts") or []
    ytd = _f(payload.get("importer_cbam_mass_ytd_t"))
    seed = bool(payload.get("seed_demo_taric"))
    demo_pack = bool(payload.get("demo_cbam_pack", payload.get("demo_pack")))
    out: list[dict] = []
    for ln in lines:
        ref = str(ln.get("shipment_ref") or "LINE")
        if source_conflicts and ln.get("field_provenance"):
            out.append({"shipment_ref": ref, "decision": "BLOCKED",
                        "compiler_decision": "BLOCKED", "entitlement_decision": "BLOCKED",
                        "evidence_states": [], "blockers": [{"engine": "reconciliation", "code": "SOURCE_VALUE_CONFLICT"}]})
            continue
        cn = "".join(ch for ch in str(ln.get("cn_code") or "") if ch.isdigit())
        qty = _f(ln.get("quantity_t"))
        val = _f(ln.get("customs_value_eur"))
        org = str(ln.get("origin_country") or "").upper()
        imp = str(ln.get("import_date") or "")
        destination = str(ln.get("destination_country") or "").upper()
        if ln.get("field_provenance") and destination not in {"AT","BE","BG","HR","CY","CZ","DK","EE","FI","FR","DE","GR","HU","IE","IT","LV","LT","LU","MT","NL","PL","PT","RO","SK","SI","ES","SE"}:
            out.append({"shipment_ref": ref, "decision": "BLOCKED",
                        "evidence_states": {"DOCUMENT_FIELDS": "UNVERIFIED"},
                        "compiler_decision": "BLOCKED", "entitlement_decision": "BLOCKED",
                        "blockers": [{"engine": "INGEST", "code": "DESTINATION_NOT_EU_OR_MISSING"}]})
            continue
        ingestion_issues = ln.get("issues") or []
        hard_ingest = {"EUR_CONVERSION_REQUIRES_RATE_SNAPSHOT",
                       "PDF_BOUNDING_BOX_UNAVAILABLE", "PDF_SOURCE_REQUIRES_REVIEW", "RAGGED_CSV_ROW",
                       "DUPLICATE_CSV_HEADERS", "ROW_LIMIT_EXCEEDED",
                       "SHEET_LIMIT_EXCEEDED"}
        if ingestion_issues and (not ln.get("review_confirmed") or
                                 hard_ingest.intersection(ingestion_issues)):
            out.append({"shipment_ref": ref, "decision": "BLOCKED",
                        "evidence_states": {"DOCUMENT_FIELDS": "UNVERIFIED"},
                        "compiler_decision": "BLOCKED", "entitlement_decision": "BLOCKED",
                        "blockers": [{"engine": "INGEST", "code": code,
                                      "reason": "Review and correct this source field before compiling."}
                                     for code in ingestion_issues]})
            continue
        if (len(cn) not in (8, 10) or qty <= 0 or val <= 0 or
                not re.fullmatch(r"20\d{2}-\d{2}-\d{2}", imp) or len(org) != 2 or
                (ln.get("field_provenance") and not str(ln.get("invoice_number") or "").strip())):
            out.append({"shipment_ref": ref, "decision": "BLOCKED",
                        "evidence_states": {}, "compiler_decision": "BLOCKED",
                        "entitlement_decision": "BLOCKED",
                        "blockers": [{"engine": "INPUT", "code": "LINE_INCOMPLETE",
                        "reason": "cn_code, quantity_t, customs_value_eur and import_date are all required - confirm the extracted candidate."}]})
            continue
        if seed:
            csv = ("cn_code,origin_country,measure_type,duty_rate\n"
                   f"{cn},{org},THIRD_COUNTRY_DUTY,0%\n")
            pub.store_snapshot("taric", pub.parse_csv(csv, "taric", imp), csv.encode())
        # evidence lifecycle per type, then fail-closed decision
        by_type: dict[str, list[dict]] = {}
        for e in ln.get("evidence", []) or []:
            by_type.setdefault(str(e.get("evidence_type") or "DOCUMENT"), []).append({
                "evidence_id": str(e.get("id") or f"E-{ref}"),
                "subject_ref": ref, "collected_at": imp,
                "verification_status": "VERIFIED" if e.get("verified") else "UNVERIFIED",
                "sha256": f"ui-{ref}-{e.get('id')}"})
        states = {k: ev.evaluate_requirement(v, as_of=imp)["state"]
                  for k, v in by_type.items()} or {"NO_EVIDENCE": "MISSING"}
        decision = de.build_decision(ref, [
            {"obligation_id": f"EVIDENCE_{k}",
             "status": ("PASS" if st == "VALID" else st),
             "severity": "BLOCKING", "required_for_release": True}
            for k, st in states.items()], as_of=imp)
        pack = None
        if demo_pack:
            # Full pack shape per app/cbam_verification_pack.py: top-level
            # monitoring_plan + operator_emissions_report, and verification_report
            # carrying installation.* + verifier.* + monitoring_plan subset +
            # statement.* (same shape as FULL_CBAM_PACK in the redacted demo).
            # Accreditation expiry 2027-12-31 keeps it current for reporting year.
            pack = {"monitoring_plan": {"version": "v1", "effective_from": "2026-01-01",
                    "installation_id": "SYN-INSTALLATION-01",
                    "production_processes": ["EAF"], "calculation_methods": ["calculation-based"],
                    "system_boundaries": ["installation"], "source_streams": ["fuels"],
                    "data_sources": ["meters"], "quality_controls": ["QA plan"]},
                "operator_emissions_report": {"reporting_period": imp[:4],
                    "installation_id": "SYN-INSTALLATION-01",
                    "goods": [{"cn_code": cn, "quantity_t": qty}],
                    "activity_levels": {"steel_t": qty},
                    "installation_emissions": {"direct_tco2": qty},
                    "production_process_emissions": {"eaf_tco2": qty},
                    "precursors": [{"material": "synthetic ferro-chromium (DEMO)",
                        "quantity_t": 2.0,
                        "specific_embedded_emissions_tco2_per_t": 1.5,
                        "value_type": "ACTUAL"}],
                    "heat_waste_gas_electricity_balance": "balanced",
                    "data_gaps": "none"},
                "verification_report": {
                    "installation": {"operator_name": "SYNTHETIC OPERATOR (DEMO)",
                        "operator_registration_number": "SYN-OP-01",
                        "installation_name": "SYNTHETIC INSTALLATION (DEMO)",
                        "installation_address": "DEMO ONLY - NOT A REAL INSTALLATION",
                        "latitude": "0.0", "longitude": "0.0",
                        "reporting_period": imp[:4]},
                    "verifier": {"verifier_name": "SYNTHETIC VERIFIER (DEMO)",
                        "verifier_address": "DEMO ONLY", "lead_auditor": "DEMO AUDITOR",
                        "accreditation_number": "SYN-ACC-01",
                        "national_accreditation_body": "DEMO NAB",
                        "accreditation_country": "DE", "accreditation_expiry": "2027-12-31",
                        "accreditation_scope": "CBAM"},
                    "monitoring_plan": {"version": "v1",
                        "production_processes": ["EAF"],
                        "calculation_methods": ["calculation-based"]},
                    "statement": {"reasonable_assurance": True,
                        "free_from_material_misstatements": True,
                        "free_from_material_nonconformities": True},
                    "findings": []}}
        try:
            comp = compile_shipment({
                "shipment_ref": ref, "cn_code": cn, "origin_country": org,
                "import_date": imp, "customs_value_eur": val, "quantity_t": qty,
                "gross_mass_kg": qty * 1000, "net_mass_kg": qty * 1000,
                "quota_remaining_t": 1000.0, "quota_balance_as_of": imp,
                "evidence": [{"id": e["evidence_id"], "evidence_type": k,
                              "sha256": e["sha256"], "issuer": "ui-session",
                              "valid_until": "2027-12-31", "document_codes": []}
                             for k, v in by_type.items() for e in v],
                "valuation": {"method": 1, "price_paid_or_payable_eur": val},
                "origin": {"non_preferential": {"country": org, "basis_ref": "UI-" + ref},
                           "preferential": {"claim_preference": False}},
                "ppwr": {"placing_on_market_date": imp,
                         "packaging_components": [{"id": "PKG-1", "heavy_metals_mg_kg": 10.0}],
                         "conformity_document_ref": "UI-DOC-01"},
                "reach_scip": {"articles": [{"id": "ART-1", "candidate_list_substances": []}]},
                "sanctions": {"parties": [{"name": "redacted-counterparty",
                                           "screened_at": imp, "source_version": "UI-SESSION"}]},
                "cbam_verification_pack": pack or {}})
            comp_d, comp_b = comp["decision"], comp["blockers"]
        except ValueError as e:
            comp_d, comp_b = "BLOCKED", [{"engine": "INPUT", "code": "COMPILER_INPUT", "reason": str(e)}]
        try:
            ent = compile_active_entitlement({
                "shipment_ref": ref, "cn_code": cn, "origin_country": org,
                "import_date": imp, "customs_value_eur": val, "quantity_t": qty,
                "steel_quota_remaining_t": 1000.0, "quota_balance_as_of": imp,
                "importer_cbam_mass_ytd_t": ytd,
                "authorised_cbam_declarant": bool(payload.get("authorised_cbam_declarant")),
                "cbam_emissions_verified": bool(payload.get("cbam_emissions_verified"))})
            ent_d = ent["decision"]
            comp_b = comp_b + [b for b in ent.get("blockers", [])
                               if b.get("code") not in {x.get("code") for x in comp_b}]
        except ValueError as e:
            ent_d = "BLOCKED"
            comp_b = comp_b + [{"engine": "INPUT", "code": "ENTITLEMENT_INPUT", "reason": str(e)}]
        evidence_blockers = [
            {"engine": "EVIDENCE", "code": f"{kind}_{state}",
             "reason": f"{kind} evidence is {state.lower()}; attach and verify the required source."}
            for kind, state in states.items() if state != "VALID"
        ]
        out.append({"shipment_ref": ref, "evidence_states": states,
                    "decision": decision["status"], "compiler_decision": comp_d,
                    "entitlement_decision": ent_d, "blockers": evidence_blockers + comp_b})
    return {"lines": out, "seed_demo_taric": seed,
            "note": ("Demo TARIC rows are synthetic 0% (as_of = import date) - replace via the regulatory import API before any real filing. "
                     "READY means EuroSetu gates pass; customs/CBAM/verifier acceptance remains external.")}
