export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: corsHeaders(),
      });
    }

    if (url.pathname === "/health") {
      return json({ ok: true, service: "brain-cloud-api", mode: "adapter" });
    }

    const origin = String(env.BRAIN_ORIGIN || "").replace(/\/$/, "");
    if (!origin || origin.includes("REPLACE_WITH_")) {
      return json({ ok: false, error: "BRAIN_ORIGIN_NOT_CONFIGURED" }, 503);
    }

    const target = new URL(url.pathname + url.search, origin);
    const headers = new Headers(request.headers);
    headers.delete("host");

    const upstream = await fetch(target, {
      method: request.method,
      headers,
      body: request.method === "GET" || request.method === "HEAD" ? undefined : request.body,
      redirect: "manual",
    });

    const out = new Response(upstream.body, upstream);
    for (const [k, v] of Object.entries(corsHeaders())) out.headers.set(k, v);
    return out;
  },
};

function corsHeaders() {
  return {
    "access-control-allow-origin": "*",
    "access-control-allow-methods": "GET,POST,PUT,PATCH,DELETE,OPTIONS",
    "access-control-allow-headers": "Content-Type, Authorization, X-V12-Agent-Key",
  };
}

function json(value, status = 200) {
  return new Response(JSON.stringify(value), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", ...corsHeaders() },
  });
}
