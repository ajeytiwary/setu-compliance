// Cloudflare Pages: only the public calculators and contact form reach the app.
const PUBLIC_POSTS = new Set([
  "/api/contact",
  "/api/tools/liability-preview",
  "/api/tools/threshold",
  "/api/tools/relief-estimate",
]);
const TEMPLATE = "/api/tools/supplier-template.csv";
const MAX_BODY_BYTES = 128 * 1024;

export async function onRequest(context) {
  const { request, env } = context;
  const path = new URL(request.url).pathname;
  if (path === TEMPLATE && request.method === "GET") {
    return env.ASSETS.fetch(new URL(path, request.url));
  }
  if (!PUBLIC_POSTS.has(path) || request.method !== "POST") {
    return new Response("Not found", { status: 404 });
  }
  if (!env.APP_ORIGIN || !env.PUBLIC_PROXY_SECRET) {
    return new Response("Public service unavailable", { status: 503 });
  }
  if (!/^application\/json(?:\s*;|$)/i.test(request.headers.get("content-type") || "")) {
    return new Response("JSON required", { status: 415 });
  }
  const declaredLength = Number(request.headers.get("content-length") || 0);
  if (declaredLength > MAX_BODY_BYTES) return new Response("Request too large", { status: 413 });
  const reader = request.body?.getReader();
  const chunks = [];
  let size = 0;
  if (reader) {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > MAX_BODY_BYTES) {
        await reader.cancel();
        return new Response("Request too large", { status: 413 });
      }
      chunks.push(value);
    }
  }
  const body = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) { body.set(chunk, offset); offset += chunk.byteLength; }
  const origin = new URL(env.APP_ORIGIN);
  if (origin.protocol !== "https:" || origin.username || origin.password || origin.pathname !== "/") {
    return new Response("Public service unavailable", { status: 503 });
  }
  let upstream;
  try {
    upstream = await fetch(new URL(path, origin), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Eurosetu-Public-Proxy-Secret": env.PUBLIC_PROXY_SECRET,
      },
      body,
      signal: AbortSignal.timeout(15000),
    });
  } catch (_) {
    return new Response("Public service temporarily unavailable", { status: 502 });
  }
  // Never forward set-cookie, WWW-Authenticate, origin details or other app headers.
  const responseBody = await upstream.arrayBuffer();
  return new Response(responseBody, {
    status: upstream.status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff",
    },
  });
}
