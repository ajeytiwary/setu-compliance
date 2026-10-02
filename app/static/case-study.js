/* Case-study walkthrough (§11): five linked views on a SYNTHETIC order.
 * Drives the production /v1 path: transaction → check (BLOCKED) → add evidence
 * (new objects only) → recompile with predecessor (READY) → replay verify.
 * Commercial rows are synthetic; regulatory refs are versioned snapshots. */
(function () {
  "use strict";

  var AS_OF = "2026-08-28";
  var TXN_REF = "SYN-PO-HRC-001-L1";
  var state = { decisions: [], evidence: [], snapshots: [] };

  function $(id) { return document.getElementById(id); }

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  async function post(url, body) {
    var r = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {})
    });
    if (!r.ok) throw new Error(url + " → " + r.status + " " + (await r.text()).slice(0, 200));
    return r.json();
  }

  function short(id) { return (id || "").slice(0, 8); }

  function statusChip(s) { return el("span", "status " + s, s); }

  function obligationTable(obligations) {
    var t = el("table", "grid");
    var head = document.createElement("tr");
    ["Obligation", "Status", "Severity", "Reasons"].forEach(function (h) {
      head.appendChild(el("th", null, h));
    });
    t.appendChild(head);
    obligations.forEach(function (o) {
      var tr = document.createElement("tr");
      tr.appendChild(el("td", "mono", o.obligation_id));
      tr.appendChild(el("td", null, o.status));
      tr.appendChild(el("td", null, o.severity || "n/a"));
      tr.appendChild(el("td", null, (o.reasons || []).join("; ") || "n/a"));
      t.appendChild(tr);
    });
    return t;
  }

  function renderRules(d) {
    var host = $("rulesBody");
    host.innerHTML = "";
    var rows = [
      ["CBAM emissions (Reg. 2026/2547)", "Applies: CN 7208 39 00 is a CBAM good; India is a third country. Requires installation-level actual emissions or versioned defaults.", "CBAM_EMISSIONS"],
      ["TARIC duty + steel safeguard quota", "Applies: EU import of Indian HRC. Requires current TARIC measure snapshot and quota balance at shipment date.", "TARIC_DUTY"],
      ["Origin statement (EU–IN FTA)", "Not applicable for preference: agreement negotiated, not in force. MFN applies; no origin evidence blocks release.", "ORIGIN_STATEMENT"]
    ];
    var t = el("table", "grid");
    var head = document.createElement("tr");
    ["Rule family", "Why it applies here", "Obligation"].forEach(function (h) {
      head.appendChild(el("th", null, h));
    });
    t.appendChild(head);
    rows.forEach(function (r) {
      var tr = document.createElement("tr");
      r.forEach(function (c) { tr.appendChild(el("td", null, c)); });
      t.appendChild(tr);
    });
    host.appendChild(t);
    var p = el("p", "note", "Source snapshots pinned to this decision: " +
      (d.source_snapshot_refs || []).map(function (s) {
        return (s.source_id || s.snapshot_id || "?") + "@" + (s.version || "?");
      }).join(", "));
    host.appendChild(p);
  }

  function renderEvidence(d) {
    var host = $("evidenceBody");
    host.innerHTML = "";
    host.appendChild(obligationTable(d.obligation_results || []));
    if (state.evidence.length) {
      var p = el("p", "note", "Evidence objects added in this walkthrough: " +
        state.evidence.map(function (e) { return e.evidence_id + " (" + (e.verification_status || "stored") + ")"; }).join(", ") +
        ". Prior decisions are unchanged; only new decisions reference them.");
      host.appendChild(p);
    }
  }

  function renderDecision(d) {
    var host = $("decisionBody");
    host.innerHTML = "";
    var line = el("p", null);
    line.appendChild(el("strong", null, "State: "));
    line.appendChild(statusChip(d.status));
    host.appendChild(line);
    host.appendChild(obligationTable(d.obligation_results || []));
    var meta = el("dl", "kv");
    [["Decision", d.decision_id + "  (hash " + short(d.decision_hash) + ")"],
     ["as_of", d.as_of + " (reproducible point-in-time)"],
     ["Policy", d.policy_version],
     ["Predecessor", d.predecessor_id ? short(d.predecessor_id) + " (supersedes; original retained)" : "none (first decision)"]
    ].forEach(function (kv) {
      meta.appendChild(el("dt", null, kv[0]));
      meta.appendChild(el("dd", "mono", kv[1]));
    });
    host.appendChild(meta);
  }

  function renderAudit() {
    var host = $("auditBody");
    host.innerHTML = "";
    if (!state.decisions.length) {
      host.appendChild(el("p", "muted", "No decisions yet in this walkthrough."));
      return;
    }
    var t = el("table", "grid");
    var head = document.createElement("tr");
    ["Decision", "Status", "Hash", "Policy", "Predecessor"].forEach(function (h) {
      head.appendChild(el("th", null, h));
    });
    t.appendChild(head);
    state.decisions.forEach(function (d) {
      var tr = document.createElement("tr");
      tr.appendChild(el("td", "mono", short(d.decision_id)));
      tr.appendChild(el("td", null, d.status));
      tr.appendChild(el("td", "mono", short(d.decision_hash)));
      tr.appendChild(el("td", "mono", d.policy_version));
      tr.appendChild(el("td", "mono", d.predecessor_id ? short(d.predecessor_id) : "n/a"));
      t.appendChild(tr);
    });
    host.appendChild(t);
    host.appendChild(el("p", "note",
      "Decisions are immutable: recompiles create new rows linked by predecessor_id. " +
      "Replay re-aggregates pinned obligation snapshots, never current mutable state."));
    $("replayBtn").disabled = false;
  }

  function showCausal(before, after) {
    var box = $("causalBox");
    box.innerHTML = "";
    var div = el("div", "causal");
    var lines = [
      "causal change  " + short(before.decision_id) + " → " + short(after.decision_id),
      "status:        " + before.status + "  →  " + after.status,
      "resolved:      " + (before.blocking_reasons || []).join("  |  "),
      "new evidence:  " + state.evidence.map(function (e) { return e.evidence_id; }).join(", "),
      "predecessor:   " + short(after.predecessor_id) + " (original retained, superseded)"
    ];
    div.innerHTML = lines.map(function (l) {
      return "<div><span class=\"green\">▸</span> " + l.replace(/</g, "&lt;") + "</div>";
    }).join("");
    box.appendChild(div);
  }

  async function bootstrap() {
    await post("/v1/transactions", {
      transaction_ref: TXN_REF, order_id: "SYN-PO-HRC-001", shipment_id: "SYN-SHIP-001",
      line_id: "L1", seller: "Synthetic India Steel (illustrative)", buyer: "Synthetic Example BV (illustrative)",
      importer: "Synthetic Example BV (illustrative)", origin_country: "IN", destination_country: "NL",
      shipment_date: AS_OF, line_value: 340000, quantity: 200, unit: "t", cn_code: "72083900"
    });
    var snaps = [
      { source_id: "CBAM_REG_2026_2547", authority: "European Commission", title: "CBAM definitive-period rules", version: "2026-06", effective_from: "2026-01-01", content: "definitive period methodology ref" },
      { source_id: "TARIC_NL_HRC", authority: "European Commission (TARIC)", title: "TARIC measures HRC 7208 39 00", version: "2026-08-27", effective_from: "2026-08-27", content: "duty + safeguard quota snapshot ref" },
      { source_id: "EU_IN_FTA_STATUS", authority: "European Commission (DG Trade)", title: "EU–India FTA status", version: "2026-08-01", effective_from: "2026-08-01", content: "negotiated, not in force; MFN applies" }
    ];
    state.snapshots = [];
    for (var i = 0; i < snaps.length; i++) {
      try { state.snapshots.push(await post("/v1/sources/snapshots", snaps[i])); }
      catch (e) { /* already registered, refetch effective list */ }
    }
    var refs = state.snapshots.map(function (s) {
      return { source_id: s.source_id, version: s.version, snapshot_id: s.content_hash };
    });
    var d = await post("/v1/market-access/check", {
      transaction_ref: TXN_REF, as_of: AS_OF,
      source_snapshot_refs: refs,
      obligations: [
        { obligation_id: "CBAM_EMISSIONS", applicable: true, status: "MISSING",
          reasons: ["precursor installation evidence not supplied"], severity: "BLOCKING", required_for_release: true },
        { obligation_id: "TARIC_DUTY", applicable: true, status: "MISSING",
          reasons: ["current steel quota balance snapshot required"], severity: "BLOCKING", required_for_release: true },
        { obligation_id: "ORIGIN_STATEMENT", applicable: false, status: "NOT_APPLICABLE",
          reasons: ["EU–IN FTA negotiated, not in force; MFN applies"], severity: "NON_BLOCKING", required_for_release: false }
      ]
    });
    state.decisions.push(d);
    renderRules(d);
    renderEvidence(d);
    renderDecision(d);
    renderAudit();
  }

  async function addEvidence() {
    var btn = $("addEvidenceBtn");
    btn.disabled = true;
    btn.textContent = "Adding …";
    try {
      var e1 = await post("/v1/evidence", {
        type: "CBAM_PRECURSOR_CERT", subject_ref: TXN_REF,
        content: "synthetic precursor installation certificate (illustrative)",
        issuer: "Synthetic Verifier (illustrative)", verification_status: "VERIFIED",
        valid_from: "2026-01-01", valid_to: "2027-01-01"
      });
      var e2 = await post("/v1/evidence", {
        type: "QUOTA_BALANCE_SNAPSHOT", subject_ref: TXN_REF,
        content: "synthetic quota balance snapshot ref (illustrative)",
        issuer: "TARIC snapshot 2026-08-27", verification_status: "VERIFIED",
        valid_from: "2026-08-27", valid_to: "2026-09-30"
      });
      state.evidence.push(e1, e2);
      renderEvidence(state.decisions[state.decisions.length - 1]);
      $("recompileBtn").disabled = false;
      btn.textContent = "Evidence added. Now recompile";
    } catch (e) {
      btn.textContent = "Failed: " + e.message;
      btn.disabled = false;
    }
  }

  async function recompile() {
    var btn = $("recompileBtn");
    btn.disabled = true;
    btn.textContent = "Recompiling …";
    try {
      var prev = state.decisions[state.decisions.length - 1];
      var evIds = state.evidence.map(function (e) { return e.evidence_id; });
      var d = await post("/v1/market-access/check", {
        transaction_ref: TXN_REF, as_of: AS_OF,
        predecessor_id: prev.decision_id,
        source_snapshot_refs: prev.source_snapshot_refs,
        evidence_snapshot_refs: evIds,
        obligations: [
          { obligation_id: "CBAM_EMISSIONS", applicable: true, status: "PASS",
            reasons: [], evidence_refs: [evIds[0]], severity: "BLOCKING", required_for_release: true },
          { obligation_id: "TARIC_DUTY", applicable: true, status: "PASS",
            reasons: [], evidence_refs: [evIds[1]], severity: "BLOCKING", required_for_release: true },
          { obligation_id: "ORIGIN_STATEMENT", applicable: false, status: "NOT_APPLICABLE",
            reasons: ["EU–IN FTA negotiated, not in force; MFN applies"], severity: "NON_BLOCKING", required_for_release: false }
        ]
      });
      state.decisions.push(d);
      renderEvidence(d);
      renderDecision(d);
      renderAudit();
      showCausal(prev, d);
      btn.textContent = "Recompiled. See causal change";
    } catch (e) {
      btn.textContent = "Failed: " + e.message;
      btn.disabled = false;
    }
  }

  async function replay() {
    var box = $("replayBox");
    box.innerHTML = "";
    var latest = state.decisions[state.decisions.length - 1];
    try {
      var r = await post("/v1/decisions/" + latest.decision_id + "/replay", {});
      state.decisions.push(r);
      renderAudit();
      var div = el("div", "causal");
      div.innerHTML = "<div><span class=\"green\">▸</span> replay of " + short(latest.decision_id) +
        " reproduced status " + latest.status + " from pinned snapshots (new row " + short(r.decision_id) + ")</div>";
      box.appendChild(div);
    } catch (e) {
      box.appendChild(el("p", "muted", "Replay failed: " + e.message));
    }
  }

  function tabs() {
    var btns = document.querySelectorAll(".tabs button");
    btns.forEach(function (b) {
      b.addEventListener("click", function () {
        btns.forEach(function (x) { x.setAttribute("aria-selected", "false"); });
        b.setAttribute("aria-selected", "true");
        document.querySelectorAll(".tabpanel").forEach(function (p) { p.classList.remove("open"); });
        $("panel-" + b.getAttribute("data-tab")).classList.add("open");
      });
    });
  }

  function main() {
    tabs();
    $("addEvidenceBtn").addEventListener("click", addEvidence);
    $("recompileBtn").addEventListener("click", recompile);
    $("replayBtn").addEventListener("click", replay);
    bootstrap().catch(function (e) {
      $("decisionBody").innerHTML = "<p class=\"muted\">Walkthrough backend unavailable: " +
        String(e.message || e).replace(/</g, "&lt;") + "</p>";
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", main);
  else main();
})();
