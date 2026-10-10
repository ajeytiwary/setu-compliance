import { describe, expect, it } from "bun:test";
import { onRequest } from "../functions/api/[[path]].js";

const base = "https://eurosetu.trade";
const env = { APP_ORIGIN: "https://app.eurosetu.trade/", PUBLIC_PROXY_SECRET: "test-secret" };
const context = (path: string, method = "POST", body = "{}", config = env) => ({
  request: new Request(base + path, { method, body: method === "POST" ? body : undefined, headers: { "content-type": "application/json" } }),
  env: config,
});

describe("public Pages API boundary", () => {
  it("denies app APIs and unsupported methods", async () => {
    expect((await onRequest(context("/api/pilot/overview"))).status).toBe(404);
    expect((await onRequest(context("/api/contact", "GET"))).status).toBe(404);
  });

  it("fails closed without proxy credentials and limits request size", async () => {
    expect((await onRequest(context("/api/contact", "POST", "{}", {}))).status).toBe(503);
    expect((await onRequest(context("/api/contact", "POST", "x".repeat(128 * 1024 + 1)))).status).toBe(413);
  });

  it("reports a clear service failure when the app origin is unavailable", async () => {
    const previous = globalThis.fetch;
    globalThis.fetch = async () => new Response("error code: 1016", { status: 530 });
    try {
      const response = await onRequest(context("/api/contact"));
      expect(response.status).toBe(503);
      expect((await response.json()).code).toBe("UPSTREAM_UNAVAILABLE");
    } finally {
      globalThis.fetch = previous;
    }
  });

  it("sends only the allowed contact request with a private backend header", async () => {
    const previous = globalThis.fetch;
    let seen: Request | undefined;
    globalThis.fetch = async (input, init) => {
      seen = new Request(input, init);
      return new Response('{"received":true}', { status: 201, headers: { "Set-Cookie": "private=true" } });
    };
    try {
      const response = await onRequest(context("/api/contact"));
      expect(response.status).toBe(201);
      expect(seen?.url).toBe("https://app.eurosetu.trade/api/contact");
      expect(seen?.headers.get("X-Eurosetu-Public-Proxy-Secret")).toBe("test-secret");
      expect(response.headers.get("Set-Cookie")).toBeNull();
    } finally {
      globalThis.fetch = previous;
    }
  });
});
