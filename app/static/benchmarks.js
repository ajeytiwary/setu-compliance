/* Public /benchmarks page (§10): renders ONLY released bundles.
 * Source: /api/benchmarks/releases → /api/benchmarks/releases/{commit}.
 * Never queries live DB rows or local run directories. */
(function () {
  "use strict";

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  function badge(cls) {
    return el("span", "tag", cls);
  }

  async function getJSON(url) {
    var r = await fetch(url, { headers: { Accept: "application/json" } });
    if (!r.ok) throw new Error(url + " → " + r.status);
    return r.json();
  }

  function renderRelease(line, summary) {
    line.innerHTML = "";
    [["RELEASE", summary.code_commit],
     ["SCHEMA", summary.schema_version],
     ["PASSED", summary.total_passed + " / " + summary.total_cases],
     ["GENERATED", (summary.generated_at || "").slice(0, 10)]
    ].forEach(function (kv) {
      var s = el("span", null, kv[0] + " " + kv[1]);
      line.appendChild(s);
    });
  }

  function renderSections(host, summary, results) {
    host.innerHTML = "";
    var bySuite = {};
    results.forEach(function (r) {
      (bySuite[r.suite_id] = bySuite[r.suite_id] || []).push(r);
    });
    Object.keys(summary.sections).forEach(function (section) {
      var suites = (summary.sections[section] || []).filter(function (s) {
        return (summary.suites || {})[s];
      });
      if (!suites.length) return;
      var sec = el("div", "bench-section");
      sec.appendChild(el("h3", "bench-section-title", section));
      var wrap = el("div", "cards bench-cards");
      suites.forEach(function (suite) {
        var meta = (summary.suites || {})[suite] || {};
        var card = el("article", "bench-card");
        var title = el("h3", null, suite);
        card.appendChild(title);
        var p = el("p", "muted",
          (meta.passed != null ? meta.passed + "/" + meta.cases + " cases passing" : "") +
          (meta.p50_ms != null ? " · p50 " + meta.p50_ms + " ms" : ""));
        card.appendChild(p);
        var tags = el("div", "proof bench-tags");
        (meta.evidence_classes || []).forEach(function (c) {
          tags.appendChild(badge(c));
        });
        card.appendChild(tags);
        var ul = el("ul", "bench-cases");
        (bySuite[suite] || []).forEach(function (r) {
          var li = document.createElement("li");
          var row = el("div", "bench-case-row");
          var a = document.createElement("a");
          a.href = "/api/benchmarks/releases/" + summary.code_commit +
            "/cases/" + encodeURIComponent(suite) + "/" + encodeURIComponent(r.case_id);
          a.target = "_blank";
          a.rel = "noopener";
          a.title = "Open machine-readable run artifact (JSON) in a new tab";
          a.textContent = r.case_id;
          row.appendChild(a);
          row.appendChild(el("span", "bench-pill " + (r.result === "PASS" ? "pass" : "fail"), r.result));
          li.appendChild(row);
          var small = el("p", "muted bench-case-meta",
            "as_of " + r.as_of + " · " + r.assertions.length + " assertions · " +
            (r.duration_ms || 0) + " ms");
          li.appendChild(small);
          ul.appendChild(li);
        });
        card.appendChild(ul);
        wrap.appendChild(card);
      });
      sec.appendChild(wrap);
      host.appendChild(sec);
    });
    var note = el("p", "note", summary.notice || "");
    host.appendChild(note);
  }

  async function main() {
    var line = document.getElementById("releaseLine");
    var host = document.getElementById("suiteTables");
    try {
      var releases = await getJSON("/api/benchmarks/releases");
      if (!releases.length) throw new Error("no releases published yet");
      var latest = releases[releases.length - 1].commit;
      var summary = await getJSON("/api/benchmarks/releases/" + latest);
      var results = await getJSON("/api/benchmarks/releases/" + latest + "/results");
      renderRelease(line, summary);
      renderSections(host, summary, results);
    } catch (e) {
      if (line) { line.innerHTML = ""; line.appendChild(el("span", null, "NO RELEASED RESULTS YET")); }
      if (host) host.innerHTML = "<p class=\"muted\">No benchmark release has been published yet. Releases are produced only by CI from passing suites (" +
        "see <code>scripts/release_benchmarks.py</code>). No aspirational numbers are shown here.</p>";
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", main);
  else main();
})();
