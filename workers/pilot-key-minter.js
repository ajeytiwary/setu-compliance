/**
 * EuroSetu pilot-key minter (Cloudflare Email + Fetch Worker).
 *
 * Flow you asked for:
 *   1. Someone emails request@eurosetu.trade -> Worker mints HS256 pilot key
 *      -> sends YOU an email FROM request@eurosetu.trade with the token IN THE
 *      BODY (copy-paste ready) -> also forwards the original as backup.
 *      You then Gmail-forward the token to the requester manually.
 *   2. Someone clicks "Request access" on the site -> site POSTs to this
 *      Worker's /notify -> Worker emails YOU from request@eurosetu.trade
 *      with the requester details + a freshly minted pilot key.
 *      Nothing is ever auto-sent to the requester.
 *
 * The minted JWT is byte-identical in shape to app/pilot_keys.py:
 *   header  {"alg":"HS256","typ":"JWT"}
 *   payload {"sub": requester email, "exp": now+days*86400, "iat": now,
 *            "tenant_id": tenant, "tenants": {tenant: roles}}
 *
 * Bindings (wrangler.toml):
 *   [[send_email]] name = "EMAIL"   (Email Sending, sender = request@ domain)
 * Secrets (wrangler secret put ...):
 *   EUROSETU_JWT_SECRET   same value as the app's env (REQUIRED)
 *   NOTIFY_SECRET         shared secret the site uses to call POST /notify
 * Vars (wrangler.toml):
 *   SENDER         default "request@eurosetu.trade" (must be onboarded domain)
 *   FORWARD_TO     default founder Gmail (backup forward destination)
 *   NOTIFY_TO      default founder Gmail (where token emails go)
 *   DEFAULT_TENANT / DEFAULT_ROLES / DEFAULT_DAYS
 *
 * Requesters can override tenant/roles/days in the subject line, e.g.:
 *   "Pilot access tenant=acme-corp roles=pilot_viewer days=14"
 * Unknown roles are dropped; empty roles fall back to DEFAULT_ROLES.
 */

const KNOWN_ROLES = new Set([
  "pilot_viewer",
  "pilot_contributor",
  "verifier",
  "admin",
]);

function b64url(bytes) {
  let s = "";
  for (const b of bytes) s += String.fromCharCode(b);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function enc(obj) {
  return b64url(new TextEncoder().encode(JSON.stringify(obj)));
}

async function hmacSha256(secret, data) {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  return new Uint8Array(
    await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(data)),
  );
}

function parseSubject(subject, env) {
  const text = String(subject || "");
  const tenant =
    (text.match(/tenant\s*=\s*([A-Za-z0-9._-]+)/i) || [])[1] ||
    env.DEFAULT_TENANT ||
    "tenant-a";
  const rolesRaw =
    (text.match(/roles\s*=\s*([A-Za-z0-9_,\s-]+)/i) || [])[1] || "";
  const roles = rolesRaw
    .split(",")
    .map((r) => r.trim())
    .filter((r) => KNOWN_ROLES.has(r));
  const daysRaw = (text.match(/days\s*=\s*(\d{1,3})/i) || [])[1];
  const days = Math.min(365, Math.max(1, parseInt(daysRaw || env.DEFAULT_DAYS || "30", 10) || 30));
  return {
    tenant,
    roles: roles.length ? roles : String(env.DEFAULT_ROLES || "pilot_viewer,pilot_contributor").split(",").map((r) => r.trim()).filter(Boolean),
    days,
  };
}

async function mintToken(secret, sub, tenant, roles, days) {
  const now = Math.floor(Date.now() / 1000);
  const header = enc({ alg: "HS256", typ: "JWT" });
  const payload = enc({
    sub,
    exp: now + days * 86400,
    iat: now,
    tenant_id: tenant,
    tenants: { [tenant]: roles },
  });
  const sig = b64url(await hmacSha256(secret, `${header}.${payload}`));
  return { token: `${header}.${payload}.${sig}`, now };
}

function esc(s) {
  return String(s ?? "").replace(/[<>&"]/g, (m) => ({"<":"&lt;",">":"&gt;","&":"&amp;",'"':"&quot;"}[m]));
}

function tokenEmailBody({ requester, tenant, roles, days, token, source }) {
  const text =
`New pilot access request (${source})

Requester: ${requester}
Tenant: ${tenant}
Roles: ${roles.join(", ")}
Days: ${days}

PILOT KEY (paste on https://eurosetu.trade/pilot):
${token}

Forward this key to ${requester} from Gmail manually.
Nothing was auto-sent to the requester.`;
  const html =
`<p>New pilot access request (${esc(source)})</p>` +
`<ul><li><b>Requester:</b> ${esc(requester)}</li>` +
`<li><b>Tenant:</b> ${esc(tenant)}</li>` +
`<li><b>Roles:</b> ${esc(roles.join(", "))}</li>` +
`<li><b>Days:</b> ${esc(String(days))}</li></ul>` +
`<p><b>PILOT KEY</b> (paste on https://eurosetu.trade/pilot):</p>` +
`<pre style="word-break:break-all;background:#0b1f18;color:#d7f0d8;padding:12px;border-radius:8px">${esc(token)}</pre>` +
`<p>Forward this key to ${esc(requester)} from Gmail manually. Nothing was auto-sent to the requester.</p>`;
  return { text, html };
}

async function sendTokenEmail(env, { requester, tenant, roles, days, token, source, detail }) {
  const from = env.SENDER || "request@eurosetu.trade";
  const primary = env.NOTIFY_TO || env.FORWARD_TO || "ajaynld13@gmail.com";
  // Demo-lead form data must also land in hello@eurosetu.trade (Email Routing
  // -> founder Gmail) so the inbox itself holds every request. Single-recipient
  // sends in a loop: safest across Email Sending binding versions.
  const extra = (env.EXTRA_NOTIFY_TO || "hello@eurosetu.trade").trim();
  const recipients = [...new Set([primary, extra].filter(Boolean))];
  const { text, html } = tokenEmailBody({ requester, tenant, roles, days, token, source });
  const fullText = detail ? `${detail}\n\n${text}` : text;
  const fullHtml = detail ? `<p>${esc(detail).replace(/\n/g, "<br>")}</p>${html}` : html;
  const sent = [];
  const failed = [];
  for (const to of recipients) {
    try {
      await env.EMAIL.send({
        to,
        from: { email: from, name: "EuroSetu access requests" },
        subject: `Pilot key for ${requester} [${tenant}]`,
        text: fullText,
        html: fullHtml,
        headers: {
          "X-EuroSetu-Key-For": requester,
          "X-EuroSetu-Tenant": tenant,
          "X-EuroSetu-Roles": roles.join(","),
          "X-EuroSetu-Days": String(days),
        },
      });
      sent.push(to);
    } catch (e) {
      // Best-effort per recipient: e.g. hello@ needs one-time destination
      // verification in the Cloudflare dashboard (code arrives via the
      // hello@ -> Gmail routing rule). Never fail the primary notify.
      console.error(`send to ${to} failed:`, e?.message || e);
      failed.push(`${to} (${e?.message || e})`);
    }
  }
  if (!sent.length) throw new Error(failed.join("; ") || "all sends failed");
  return sent.join(", ") + (failed.length ? ` [failed: ${failed.join("; ")}]` : "");
}

export default {
  // Path 1: inbound email to request@eurosetu.trade
  async email(message, env, ctx) {
    const secret = env.EUROSETU_JWT_SECRET;
    const dest = env.FORWARD_TO || env.NOTIFY_TO || "ajaynld13@gmail.com";
    if (!secret) {
      await message.forward(dest);
      return;
    }
    const requester = String(message.from || "").trim().toLowerCase();
    const { tenant, roles, days } = parseSubject(message.headers.get("subject"), env);
    const { token } = await mintToken(secret, requester, tenant, roles, days);

    // Primary: copy-paste-ready email IN THE BODY via Email Sending.
    // If sending is not yet onboarded this throws — fall back to headers.
    try {
      if (!env.EMAIL) throw new Error("EMAIL binding missing");
      await sendTokenEmail(env, { requester, tenant, roles, days, token, source: "email to request@" });
    } catch (e) {
      console.error("sendTokenEmail failed, falling back to forward-only:", e?.message || e);
    }
    // Backup: forward the ORIGINAL with the key in headers (always works).
    await message.forward(dest, new Headers({
      "X-EuroSetu-Pilot-Key": token,
      "X-EuroSetu-Key-For": requester,
      "X-EuroSetu-Tenant": tenant,
      "X-EuroSetu-Roles": roles.join(","),
      "X-EuroSetu-Days": String(days),
    }));
  },

  // Path 2: site button -> POST /notify -> email founder from request@
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (request.method === "GET" && (url.pathname === "/" || url.pathname === "/health")) {
      return Response.json({ ok: true, worker: "eurosetu-pilot-key-minter" });
    }
    if (request.method !== "POST" || url.pathname !== "/notify") {
      return Response.json({ ok: false, error: "POST /notify only" }, { status: 404 });
    }
    let body;
    try { body = await request.json(); }
    catch { return Response.json({ ok: false, error: "invalid JSON" }, { status: 400 }); }
    if (env.NOTIFY_SECRET && body.secret !== env.NOTIFY_SECRET) {
      return Response.json({ ok: false, error: "bad secret" }, { status: 401 });
    }
    const secret = env.EUROSETU_JWT_SECRET;
    if (!secret) return Response.json({ ok: false, error: "server not configured" }, { status: 503 });
    const requester = String(body.email || "").trim().toLowerCase();
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(requester)) {
      return Response.json({ ok: false, error: "valid email required" }, { status: 422 });
    }
    const tenant = String(body.tenant || env.DEFAULT_TENANT || "tenant-a").trim() || "tenant-a";
    const roles = Array.isArray(body.roles) && body.roles.length
      ? body.roles.filter((r) => KNOWN_ROLES.has(r))
      : String(env.DEFAULT_ROLES || "pilot_viewer,pilot_contributor").split(",").map((r) => r.trim()).filter(Boolean);
    const days = Math.min(365, Math.max(1, parseInt(body.days || env.DEFAULT_DAYS || "30", 10) || 30));
    const { token } = await mintToken(secret, requester, tenant, roles, days);
    const detail = `Site ${body.kind || "request"}: ${body.name || ""} <${requester}>` +
      (body.company ? ` · ${body.company}` : "") +
      (body.role ? ` · ${body.role}` : "") +
      (body.topic ? ` · ${body.topic}` : "") +
      (body.message ? `\n"${body.message}"` : "");
    try {
      const to = await sendTokenEmail(env, { requester, tenant, roles, days, token, source: `site ${body.kind || "button"}`, detail });
      return Response.json({ ok: true, emailed_to: to }, { status: 200 });
    } catch (e) {
      return Response.json({ ok: false, error: String(e?.message || e) }, { status: 502 });
    }
  },
};
