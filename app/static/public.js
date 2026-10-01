/* EuroSetu public site interactions.
 *
 * Two jobs, both delegated so they work on every page that loads this file:
 *   1. Commercial cards reveal a "Contact now" call to action when clicked.
 *   2. That call to action opens a contact dialog posting to POST /api/contact.
 *
 * The dialog markup is injected at runtime so index/trust/case-study do not have
 * to duplicate it. No dependencies, no build step.
 */
(function () {
  "use strict";

  var MODAL_ID = "contactModal";
  var DEFAULT_TOPIC = "General enquiry";
  var topicEl = null;
  var lastFocus = null;

  /* ------------------------------------------------------------------ dialog */

  function buildModal() {
    if (document.getElementById(MODAL_ID)) {
      topicEl = document.getElementById("contactInterest");
      return;
    }
    var wrap = document.createElement("div");
    wrap.id = MODAL_ID;
    wrap.className = "modal";
    wrap.hidden = true;
    wrap.innerHTML = [
      '<div class="modal-backdrop" data-close="1"></div>',
      '<div class="modal-card" role="dialog" aria-modal="true" aria-labelledby="contactTitle">',
      '<button type="button" class="modal-close" data-close="1" aria-label="Close contact form">\u00d7</button>',
      '<p class="eyebrow">CONTACT</p>',
      '<h2 id="contactTitle">Talk to the founders</h2>',
      '<p class="lede">Tell us the shipment problem. You get a scoped next step and a named owner, not a brochure.</p>',
      '<p class="interest">Interest: <b id="contactInterest">' + DEFAULT_TOPIC + "</b></p>",
      '<form id="contactForm" novalidate>',
      '<div class="form-grid">',
      '<label>Full name<input id="contactName" name="name" autocomplete="name" placeholder="Priya Sharma" required></label>',
      '<label>Work email<input id="contactEmail" name="email" type="email" autocomplete="email" placeholder="priya@company.com" required></label>',
      '<label>Company<input id="contactCompany" name="company" autocomplete="organization" placeholder="Company"></label>',
      "</div>",
      '<label class="full">What is the shipment problem?<textarea id="contactMessage" name="message" placeholder="e.g. CBAM exposure on EU-bound HRC, steel quota balance, supplier precursor evidence"></textarea></label>',
      '<div class="hp" aria-hidden="true"><label>Website<input id="contactWebsite" name="website" tabindex="-1" autocomplete="off"></label></div>',
      '<button type="submit" id="contactSubmit">Send enquiry \u2192</button>',
      '<p id="contactStatus" class="form-status" role="status" aria-live="polite"></p>',
      "</form>",
      "</div>"
    ].join("");
    document.body.appendChild(wrap);
    topicEl = wrap.querySelector("#contactInterest");

    wrap.addEventListener("click", function (e) {
      if (e.target.getAttribute && e.target.getAttribute("data-close")) closeModal();
    });
    wrap.querySelector("#contactForm").addEventListener("submit", submitContact);
    firstField().addEventListener("keydown", trapTab);
  }

  function modal() { return document.getElementById(MODAL_ID); }
  function firstField() { return document.getElementById("contactName"); }

  function openModal(topic) {
    buildModal();
    var m = modal();
    var name = (topic || "").trim() || DEFAULT_TOPIC;
    topicEl.textContent = name;
    topicEl.setAttribute("data-topic", name);

    var status = document.getElementById("contactStatus");
    status.textContent = "";
    status.className = "form-status";

    lastFocus = document.activeElement;
    m.hidden = false;
    document.documentElement.classList.add("modal-open");
    firstField().focus();
  }

  function closeModal() {
    var m = modal();
    if (!m || m.hidden) return;
    m.hidden = true;
    document.documentElement.classList.remove("modal-open");
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  function trapTab(e) {
    if (e.key !== "Tab") return;
    var m = modal();
    var items = m.querySelectorAll("input, textarea, button, select, a[href]");
    var list = [];
    for (var i = 0; i < items.length; i++) {
      if (items[i].offsetParent !== null || items[i] === document.activeElement) list.push(items[i]);
    }
    if (!list.length) return;
    var first = list[0];
    var last = list[list.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  }

  /* --------------------------------------------------------------- submission */

  function status(msg, kind) {
    var el = document.getElementById("contactStatus");
    el.textContent = msg;
    el.className = "form-status" + (kind ? " " + kind : "");
  }

  function submitContact(e) {
    e.preventDefault();
    var btn = document.getElementById("contactSubmit");
    var payload = {
      name: document.getElementById("contactName").value,
      work_email: document.getElementById("contactEmail").value,
      company: document.getElementById("contactCompany").value,
      topic: topicEl.getAttribute("data-topic") || DEFAULT_TOPIC,
      message: document.getElementById("contactMessage").value,
      website: document.getElementById("contactWebsite").value
    };
    if (!payload.name.trim()) return status("Please add your name.", "bad");
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(payload.work_email.trim())) {
      return status("Please use a valid work email.", "bad");
    }

    btn.disabled = true;
    btn.textContent = "Sending\u2026";
    status("Sending your enquiry\u2026");

    fetch("/api/contact", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }).then(function (res) {
      if (res.status === 201) {
        status("Received. We reply within two working days.", "good");
        btn.textContent = "Sent \u2713";
        document.getElementById("contactForm").reset();
        return;
      }
      return res.json().catch(function () { return {}; }).then(function (body) {
        throw new Error(typeof body.detail === "string" ? body.detail : "Request failed");
      });
    }).catch(function (err) {
      btn.disabled = false;
      btn.textContent = "Send enquiry \u2192";
      status((err && err.message) || "Could not send. Please retry.", "bad");
    });
  }

  /* ------------------------------------------------------------------- cards
   *
   * Every commercial box on the site (service tiers, control-plane steps,
   * pricing rows, team cards, trust and case-study cards) is a `.pick`. Clicking
   * it flips the card into an active state and the "Contact now" button is
   * injected into that card on first activation. Nothing is exposed until the
   * visitor asks for it, and no card markup has to duplicate the button.
   */

  var PICK_SELECTOR = ".cards article, .three article, .pricing > div, " +
                      ".team-grid article, .proof span";

  function cardTopic(card) {
    var heading = card.querySelector("h3, strong, h2");
    var text = heading ? heading.textContent : "";
    return text.replace(/\s+/g, " ").trim().slice(0, 120) || DEFAULT_TOPIC;
  }

  function ensureCta(card) {
    var cta = card.querySelector(".contact-now");
    if (cta) { cta.focus(); return cta; }

    cta = document.createElement("button");
    cta.type = "button";
    cta.className = "contact-now";
    cta.textContent = "Contact now \u2192";
    cta.setAttribute("data-topic", cardTopic(card));
    card.appendChild(cta);
    return cta;
  }

  function activateCard(card) {
    var alreadyOpen = card.classList.contains("open");
    card.classList.add("open");
    card.setAttribute("aria-expanded", "true");
    if (!alreadyOpen) ensureCta(card).focus();
  }

  document.addEventListener("click", function (e) {
    var t = e.target;
    if (!t || !t.closest) return;

    var cta = t.closest(".contact-now");
    if (cta) {
      e.preventDefault();
      openModal(cta.getAttribute("data-topic"));
      return;
    }
    var card = t.closest(PICK_SELECTOR);
    if (card) {
      e.preventDefault();
      activateCard(card);
      return;
    }
    if (t.id === "contactModal" || (t.getAttribute && t.getAttribute("data-close"))) closeModal();
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") { closeModal(); return; }
    if (e.key !== "Enter" && e.key !== " ") return;
    var el = e.target;
    if (!el || !el.closest) return;
    if (el.classList && el.classList.contains("contact-now")) return; // native button
    var card = el.closest(PICK_SELECTOR);
    if (card) {
      e.preventDefault();
      activateCard(card);
    }
  });

  // Cards are clickable affordances: announce them to keyboard and screen-reader
  // users without putting a button inside a button.
  function wireCards() {
    buildModal();
    var picks = document.querySelectorAll(PICK_SELECTOR);
    for (var i = 0; i < picks.length; i++) {
      picks[i].classList.add("pick");
      picks[i].setAttribute("role", "button");
      picks[i].setAttribute("tabindex", "0");
      picks[i].setAttribute("aria-expanded", "false");
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", wireCards);
  } else {
    wireCards();
  }
})();
