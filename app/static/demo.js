/* Setu lead-gated demo — designer pass.
   Gate: POST /api/leads -> localStorage token -> x-setu-lead-token header.
   Display: KPI cards, drilldown filters, simulator, evidence form, queue. */
const eur = n => new Intl.NumberFormat("en-IE", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(n || 0);
const esc = s => String(s ?? "").replace(/[&<>"']/g, m => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[m]));
const pct = (n, d) => d ? Math.round(100 * n / d) : 0;
const TOKEN_KEY = "setu_lead_token";
let riskData = null;
let filter = { country: null, rule: null };

const token = () => localStorage.getItem(TOKEN_KEY) || "";
const authHeaders = (extra = {}) => ({ ...extra, "x-setu-lead-token": token() });
async function api(path, opts = {}) {
  const res = await fetch(path, { ...opts, headers: authHeaders({ "Content-Type": "application/json", ...(opts.headers || {}) }) });
  if (res.status === 403) { showGate(); throw new Error("forbidden"); }
  return res;
}

function showGate() {
  document.querySelector("#gate").hidden = false;
  document.querySelector("#demo").hidden = true;
}
function showDemo(name, company) {
  document.querySelector("#gate").hidden = true;
  document.querySelector("#demo").hidden = false;
  if (name) {
    const chip = document.querySelector("#accessChip");
    chip.hidden = false;
    chip.textContent = "Access: " + name + (company ? " · " + company : "");
    document.querySelector("#welcomeLine").textContent =
      "Welcome, " + name + " — explore the working system below. Filter by destination or rule, simulate fixes, raise evidence requests.";
  }
}

function renderRisk() {
  const m = riskData.metrics;
  document.querySelector("#kpis").innerHTML = [
    ["EU order book", eur(m.eu_order_book_eur), "total EU-bound value"],
    ["Market ready", eur(m.market_ready_value_eur), (m.market_ready_value_pct ?? 0) + "% of book"],
    ["Revenue at risk", eur(m.revenue_at_risk_eur), "blocked by evidence/rules"],
    ["Ready", (m.market_ready_value_pct ?? 0) + "%", "share of value shippable"],
  ].map((x, i) =>
    '<div class="card' + (i === 2 ? " danger" : i === 1 ? " accent" : "") + '"><div class="label">' + x[0] +
    '</div><div class="value">' + x[1] + '</div><div class="sub">' + esc(x[2]) + "</div></div>"
  ).join("");

  document.querySelector("#countries").innerHTML = riskData.countries.map(c =>
    '<div class="row clickable' + (filter.country === c.country ? " selected" : "") + '" data-country="' + esc(c.country) + '"><div class="kv"><span class="t">' + esc(c.country) +
    '</span><span class="v bad">' + eur(c.at_risk_value_eur) + '</span></div><div class="bar"><i style="width:' +
    pct(c.at_risk_value_eur, c.total_value_eur) + '%"></i></div><div class="muted" style="font-size:12px">' +
    eur(c.total_value_eur) + " total</div></div>"
  ).join("") || '<div class="muted">No destinations.</div>';

  document.querySelector("#rules").innerHTML = riskData.rule_risk.map(r =>
    '<div class="row clickable' + (filter.rule === r.code ? " selected" : "") + '" data-rule="' + esc(r.code) + '"><div class="kv"><span class="t">' + esc(r.code) +
    '</span><span class="v bad">' + eur(r.value_eur) + "</span></div></div>"
  ).join("") || '<div class="muted">No blocking rules.</div>';

  const rows = riskData.drilldown.filter(x =>
    (!filter.country || x.country === filter.country) && (!filter.rule || x.blocker.code === filter.rule));
  document.querySelector("#breadcrumb").textContent = ["Portfolio", filter.country, filter.rule].filter(Boolean).join(" → ");
  document.querySelector("#activeFilters").innerHTML =
    (filter.country ? '<span class="chip">' + esc(filter.country) + '<button data-clear="country" aria-label="clear">×</button></span>' : "") +
    (filter.rule ? '<span class="chip">' + esc(filter.rule) + '<button data-clear="rule" aria-label="clear">×</button></span>' : "");

  document.querySelector("#drilldown").innerHTML = rows.length ? rows.map(x =>
    '<div class="drill"><div class="drill-head"><span><b>' + esc(x.shipment_no) + "</b> · " + esc(x.country) +
    '</span><span class="v">' + eur(x.value_eur) + "</span></div>" +
    '<div class="bad blocker">' + esc(x.blocker.code) + " · " + esc(x.blocker.label) + " · " + esc(x.blocker.status) + "</div>" +
    '<div class="muted">' + esc(x.blocker.notes || "Evidence or rule condition incomplete") + "</div>" +
    '<div class="sim-row"><button class="secondary small simulate" data-shipment="' + esc(x.shipment_id) +
    '" data-rule="' + esc(x.blocker.code) + '">Simulate fix</button></div>' +
    (x.suppliers || []).map(s =>
      '<div class="supplier"><b>' + esc(s.supplier_name) + "</b> · " + esc(s.material || "material") +
      '<br><span class="muted">Needed: ' + esc(s.required_evidence_type || x.blocker.code) +
      " · owner: " + esc(s.owner || "unassigned") + " · due: " + esc(s.due_date || "unset") + "</span>" +
      '<br><button class="small prefill" data-shipment="' + esc(x.shipment_id) + '" data-supplier="' + esc(s.supplier_id) +
      '" data-evidence="' + esc(s.required_evidence_type || x.blocker.code) + '">Request evidence</button></div>'
    ).join("") + "</div>"
  ).join("") : '<div class="row muted">No blockers for this selection.</div>';

  document.querySelectorAll("[data-country]").forEach(e => e.onclick = () => {
    filter.country = filter.country === e.dataset.country ? null : e.dataset.country; renderRisk();
  });
  document.querySelectorAll("[data-rule]").forEach(e => e.onclick = () => {
    filter.rule = filter.rule === e.dataset.rule ? null : e.dataset.rule; renderRisk();
  });
  document.querySelectorAll("[data-clear]").forEach(e => e.onclick = () => {
    filter[e.dataset.clear] = null; renderRisk();
  });
  document.querySelectorAll(".prefill").forEach(e => e.onclick = () => {
    document.querySelector("#shipmentId").value = e.dataset.shipment;
    document.querySelector("#supplierId").value = e.dataset.supplier;
    document.querySelector("#evidenceType").value = e.dataset.evidence;
    document.querySelector("#owner").focus();
    document.querySelector("#requestForm").scrollIntoView({ behavior: "smooth", block: "center" });
  });
  document.querySelectorAll(".simulate").forEach(e => e.onclick = () => simulate(e.dataset.shipment, e.dataset.rule));
}

async function simulate(shipment, rule) {
  const box = document.querySelector("#simulation");
  const raw = prompt("Estimated remediation cost (€)", "5000");
  if (raw === null) return;
  const cost = Math.max(0, Number(raw) || 0);
  box.textContent = "Simulating…";
  const res = await api("/api/market-access/shipments/" + encodeURIComponent(shipment) + "/simulate-remediation",
    { method: "POST", body: JSON.stringify({ requirement_code: rule, estimated_cost_eur: cost }) });
  const s = await res.json();
  if (!res.ok) { box.textContent = s.detail || "Simulation failed"; return; }
  box.classList.remove("muted");
  box.innerHTML = "<b>" + esc(s.shipment_no) + " · " + esc(s.requirement.code) + " → PASS</b>" +
    '<div class="' + (s.after.market_ready ? "good" : "bad") + '">' +
    (s.after.market_ready ? "Shipment becomes market-ready" : "Shipment remains blocked") + "</div>" +
    "<div>Revenue unlocked: <b>" + eur(s.after.revenue_unlocked_eur) + "</b> · remediation cost: " +
    eur(s.after.estimated_remediation_cost_eur) + " · net value unlocked: <b>" + eur(s.after.net_value_unlocked_eur) + "</b></div>" +
    '<div class="muted">' + (s.after.next_blocker ? "Next blocker: " + esc(s.after.next_blocker.code) + " — " + esc(s.after.next_blocker.label) : "No remaining blocking requirements.") + "</div>" +
    '<div class="muted">What-if only — no compliance state was changed.</div>';
}

async function loadRemediation() {
  const r = await (await api("/api/remediation")).json();
  document.querySelector("#remediation").innerHTML =
    "<p><b>" + r.open_requests + "</b> open · " +
    '<span class="bad">' + eur(r.revenue_at_risk_eur) + " linked revenue at risk</span></p>" +
    (r.requests || []).map(x =>
      '<div class="row"><div class="kv"><span class="t"><b>' + esc(x.shipment_no) + "</b> → " + esc(x.supplier_name) +
      '</span><span class="v ' + (x.status === "RESOLVED" ? "good" : "bad") + '">' + esc(x.status) + "</span></div>" +
      '<div class="muted">' + esc(x.evidence_type) + " · " + esc(x.owner) + " · due " + esc(x.due_date || "unset") + "</div></div>"
    ).join("");
}

async function loadAll() {
  riskData = await (await api("/api/market-access/risk-drilldown")).json();
  renderRisk();
  await loadRemediation();
  const i = await (await api("/api/integrations")).json();
  document.querySelector("#integrations").innerHTML = (i.connectors || []).map(c =>
    '<div class="row"><div class="kv"><span class="t"><b>' + esc(c.label) + "</b> · " + esc(c.canonical_type) +
    '</span><span class="v muted" style="font-size:12px">' + (c.live_api_configured ? "live endpoint configured" : "CSV/sample ready") + "</span></div></div>"
  ).join("");
}

document.querySelector("#leadForm").addEventListener("submit", async e => {
  e.preventDefault();
  const err = document.querySelector("#leadError");
  const btn = document.querySelector("#leadSubmit");
  err.hidden = true;
  const payload = {
    name: document.querySelector("#leadName").value.trim(),
    work_email: document.querySelector("#leadEmail").value.trim(),
    company: document.querySelector("#leadCompany").value.trim(),
    role: document.querySelector("#leadRole").value || null,
    message: document.querySelector("#leadMessage").value.trim() || null,
  };
  if (!payload.name || !payload.company || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(payload.work_email)) {
    err.textContent = "Please share your name, a valid work email and company.";
    err.hidden = false;
    return;
  }
  btn.disabled = true;
  btn.textContent = "Unlocking…";
  try {
    const res = await fetch("/api/leads", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    const out = await res.json();
    if (!res.ok) throw new Error(out.detail || "Could not unlock the demo");
    localStorage.setItem(TOKEN_KEY, out.token);
    showDemo(payload.name, payload.company);
    await loadAll();
  } catch (ex) {
    err.textContent = ex.message;
    err.hidden = false;
  } finally {
    btn.disabled = false;
    btn.textContent = "Unlock the demo →";
  }
});

document.querySelector("#requestForm").addEventListener("submit", async e => {
  e.preventDefault();
  const status = document.querySelector("#formStatus");
  const payload = {
    shipment_id: document.querySelector("#shipmentId").value,
    supplier_id: document.querySelector("#supplierId").value,
    requirement_code: document.querySelector("#requirementCode").value || "SUPPLIER_DATA",
    evidence_type: document.querySelector("#evidenceType").value,
    owner: document.querySelector("#owner").value,
    due_date: document.querySelector("#dueDate").value || null,
    message: document.querySelector("#message").value || null,
  };
  const res = await api("/api/remediation/requests", { method: "POST", body: JSON.stringify(payload) });
  const out = await res.json();
  status.textContent = res.ok ? " Request created" : " " + (out.detail || "Request failed");
  if (res.ok) {
    e.target.reset();
    document.querySelector("#requirementCode").value = "SUPPLIER_DATA";
    await loadRemediation();
    riskData = await (await api("/api/market-access/risk-drilldown")).json();
    renderRisk();
  }
});

(async function init() {
  const t = token();
  if (!t) { showGate(); return; }
  try {
    const res = await fetch("/api/leads/verify", { headers: { "x-setu-lead-token": t } });
    const out = await res.json();
    if (!out.valid) { localStorage.removeItem(TOKEN_KEY); showGate(); return; }
    showDemo(out.name, out.company);
    await loadAll();
  } catch { showGate(); }
})();
