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
    body = hero("PRICING", "One tier. Priced like infrastructure, not consultancy.",
        "Start with a paid pilot on your own shipments. Stay for the control plane.")
    body += '''<section><div class="tool-grid">
<article><h3>Diagnostic - ₹2-3L</h3><p>Two-week evidence and liability diagnostic on your 12-month EU-bound book. Shipment-level blockers, revenue at risk, supplier chase list. Fixed fee, fixed scope.</p></article>
<article><h3>Pilot - ₹6.5-7.5L</h3><p>90-day paid pilot: live control plane on your shipments, supplier portal, verification workflow, declaration pack. Converts to production on success.</p></article>
<article><h3>Enterprise - ₹18-25L</h3><p>Multi-facility, multi-importer rollout with integrations (SAP SD/MM, MES, EMS), SSO, and verifier workflows.</p></article>
<article><h3>Production - €6-150k/yr</h3><p>Annual platform by EU-bound shipment volume and importer count. Includes versioned rule updates, audit exports and support. Certificate costs themselves are always pass-through to the registry.</p></article>
</div>
<p style="margin-top:18px"><b>Every tier includes:</b> versioned EU rule tables (TARIC, safeguard, CBAM, origin), supplier portal, evidence graph, records vault with checksums, threshold monitor, audit log, declaration-pack export. No per-certificate margin. No success fees.</p></section>'''
    body += _cta_row() + _rules_footer()
    return ("Pricing - EuroSetu", "Diagnostic, pilot, enterprise and production pricing.", body)


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
<details><summary>How do saved ledgers and monthly statements work?</summary><p>Preview tools run in session and store nothing. Pilot and production workspaces save every ledger, retest the 50 t threshold on each import, and export the declaration pack as a zip with figures, verification status and audit log. <a href="/account">Account.</a></p></details>
<details><summary>How does authentication work? Is there two-factor?</summary><p>Demo access uses a lead token; pilot APIs use HS256 bearer keys scoped to a tenant with roles (owner, ops, finance, read-only auditor); supplier links are per-request tokens that expire. Authenticator-app second factor with recovery codes and device lists ships with production accounts; pilot tenants get it on request. <a href="/security">Security.</a></p></details>
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
