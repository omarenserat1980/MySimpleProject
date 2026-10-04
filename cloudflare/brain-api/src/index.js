export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    const allowedOrigin = String(env.BRAIN_ALLOWED_ORIGIN || "https://omarenserat1980.github.io");
    const requestOrigin = request.headers.get("Origin") || "";
    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: corsHeaders(requestOrigin, allowedOrigin),
      });
    }

    if (url.pathname === "/health") {
      return json({ ok: true, service: "brain-cloud-api", mode: "adapter" });
    }

    if (url.pathname === "/api/payments/paytabs/callback") {
      // PayTabs callback must be handled by the protected BRAIN origin.
      // Do not accept or mark payments verified in the public proxy itself.
      return json({ ok: false, error: "PAYTABS_CALLBACK_ORIGIN_REQUIRED" }, 503, requestOrigin, allowedOrigin);
    }

    const origin = String(env.BRAIN_ORIGIN || "").replace(/\/$/, "");
    if (!origin || origin.includes("REPLACE_WITH_")) {
      return json({ ok: false, error: "BRAIN_ORIGIN_NOT_CONFIGURED" }, 503);
    }

    const target = new URL(url.pathname + url.search, origin);
    const headers = new Headers(request.headers);
    headers.delete("host");

    let upstream;
    try {
      upstream = await fetch(target, {
      method: request.method,
      headers,
      body: request.method === "GET" || request.method === "HEAD" ? undefined : request.body,
      redirect: "manual",
      });
    } catch (error) {
      return json({ ok: false, error: "UPSTREAM_UNAVAILABLE" }, 502, requestOrigin, allowedOrigin);
    }

    const out = new Response(upstream.body, upstream);
    for (const [k, v] of Object.entries(corsHeaders(requestOrigin, allowedOrigin))) out.headers.set(k, v);
    return out;
  },
};

function corsHeaders(requestOrigin = "", allowedOrigin = "https://omarenserat1980.github.io") {
  const allowOrigin = requestOrigin === allowedOrigin ? allowedOrigin : allowedOrigin;
  return {
    "access-control-allow-origin": allowOrigin,
    "access-control-allow-methods": "GET,POST,PUT,PATCH,DELETE,OPTIONS",
    "access-control-allow-headers": "Content-Type, Authorization, X-V12-Agent-Key",
  };
}

function json(value, status = 200, requestOrigin = "", allowedOrigin = "https://omarenserat1980.github.io") {
  return new Response(JSON.stringify(value), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", ...corsHeaders(requestOrigin, allowedOrigin) },
  });
}
