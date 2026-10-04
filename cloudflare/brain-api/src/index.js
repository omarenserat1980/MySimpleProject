const DEFAULT_ALLOWED_ORIGIN = "https://omarenserat1980.github.io";
const PAYTABS_BASE_URL = "https://secure-jordan.paytabs.com";

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const allowedOrigin = String(env.BRAIN_ALLOWED_ORIGIN || DEFAULT_ALLOWED_ORIGIN);
    const requestOrigin = request.headers.get("Origin") || "";

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders(requestOrigin, allowedOrigin) });
    }

    if (url.pathname === "/health") {
      const db = Boolean(env.BRAIN_DB);
      return json({ ok: true, service: "brain-cloud-api", mode: "commercial-edge", d1: db ? "CONFIGURED" : "NOT_CONFIGURED" }, 200, requestOrigin, allowedOrigin);
    }

    if (url.pathname === "/api/orders" && request.method === "POST") {
      return createCommercialOrder(request, env, requestOrigin, allowedOrigin);
    }

    if (url.pathname === "/api/payments/paytabs/create" && request.method === "POST") {
      return createPayTabsPayment(request, env, url, requestOrigin, allowedOrigin);
    }

    if (url.pathname === "/api/orders" && request.method === "GET") {
      return listClientOrders(request, env, requestOrigin, allowedOrigin);
    }

    if (url.pathname === "/api/payments/paytabs/callback" && request.method === "POST") {
      return handlePayTabsCallback(request, env, requestOrigin, allowedOrigin);
    }
    if (url.pathname === "/api/payments/paytabs/return" && request.method === "POST") {
      return handlePayTabsReturn(request, env, allowedOrigin);
    }
    if (url.pathname === "/api/cinema/checkout" && request.method === "POST") {
      return createCinemaCheckout(request, env, url, requestOrigin, allowedOrigin);
    }
    if (url.pathname === "/api/cinema/access" && request.method === "GET") {
      return cinemaAccess(request, env, requestOrigin, allowedOrigin);
    }
    if (url.pathname === "/api/cinema/stream" && request.method === "GET") {
      return cinemaStream(request, env, requestOrigin, allowedOrigin);
    }

    const origin = String(env.BRAIN_ORIGIN || "").replace(/\/$/, "");
    if (!origin || origin.includes("REPLACE_WITH_")) {
      return json({ ok: false, error: "BRAIN_ORIGIN_NOT_CONFIGURED" }, 503, requestOrigin, allowedOrigin);
    }

    const target = new URL(url.pathname + url.search, origin);
    const headers = new Headers(request.headers);
    headers.delete("host");

    try {
      const upstream = await fetch(target, {
        method: request.method,
        headers,
        body: request.method === "GET" || request.method === "HEAD" ? undefined : request.body,
        redirect: "manual",
      });
      const out = new Response(upstream.body, upstream);
      for (const [k, v] of Object.entries(corsHeaders(requestOrigin, allowedOrigin))) out.headers.set(k, v);
      return out;
    } catch {
      return json({ ok: false, error: "UPSTREAM_UNAVAILABLE" }, 502, requestOrigin, allowedOrigin);
    }
  },
};



async function createCinemaCheckout(request, env, url, requestOrigin, allowedOrigin) {
  if (!env.BRAIN_DB) return json({ ok: false, error: "D1_NOT_CONFIGURED" }, 503, requestOrigin, allowedOrigin);
  const serverKey = String(env.PAYTABS_SERVER_KEY || "");
  const profileId = String(env.PAYTABS_PROFILE_ID || "");
  if (!serverKey || !profileId) return json({ ok: false, error: "PAYTABS_SECRETS_NOT_CONFIGURED" }, 503, requestOrigin, allowedOrigin);

  let body;
  try { body = await request.json(); } catch { return json({ ok: false, error: "INVALID_JSON" }, 400, requestOrigin, allowedOrigin); }
  const filmId = String(body.film_id || "").trim();
  const email = String(body.email || "").trim().toLowerCase();
  if (filmId !== "brain-last-light-city") return json({ ok: false, error: "FILM_NOT_FOUND" }, 404, requestOrigin, allowedOrigin);
  if (!/^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/.test(email)) return json({ ok: false, error: "VALID_EMAIL_REQUIRED" }, 400, requestOrigin, allowedOrigin);

  const orderId = "BRAIN-CIN-" + new Date().toISOString().slice(0,10).replaceAll("-","") + "-" + crypto.randomUUID().slice(0,8).toUpperCase();
  const accessToken = crypto.randomUUID().replaceAll("-","") + crypto.randomUUID().replaceAll("-","");
  const tokenHash = await sha256Hex(new TextEncoder().encode(accessToken));
  const amount = 0.99;
  const currency = "JOD";

  await env.BRAIN_DB.prepare(
    "INSERT INTO orders (order_id, service, plan, amount, currency, state, client_email) VALUES (?, 'CINEMA_FILM', ?, ?, ?, 'NEW', ?)"
  ).bind(orderId, filmId + ":RENT", amount, currency, email).run();
  await env.BRAIN_DB.prepare(
    "INSERT INTO cinema_entitlements (order_id, film_id, token_hash, state) VALUES (?, ?, ?, 'PENDING')"
  ).bind(orderId, filmId, tokenHash).run();
  await recordOrderEvent(env, orderId, null, "NEW", "CINEMA_ORDER_CREATED", { film_id: filmId, amount, currency, client_email: email });

  const callback = url.origin + "/api/payments/paytabs/callback";
  const returnUrl = url.origin + "/api/payments/paytabs/return?cinema_token=" + encodeURIComponent(accessToken);
  const payload = {
    profile_id: Number(profileId),
    tran_type: "sale",
    tran_class: "ecom",
    cart_id: orderId,
    cart_currency: currency,
    cart_amount: amount,
    cart_description: "BRAIN Cinema - " + filmId,
    callback,
    return: returnUrl,
  };

  const response = await fetch(PAYTABS_BASE_URL + "/payment/request", {
    method: "POST",
    headers: { Authorization: serverKey, "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const result = await response.json().catch(() => ({}));
  if (!response.ok || !result.tran_ref || !result.redirect_url) {
    await env.BRAIN_DB.prepare("UPDATE orders SET state = 'FAILED' WHERE order_id = ?").bind(orderId).run();
    await recordOrderEvent(env, orderId, "NEW", "FAILED", "PAYMENT_REQUEST_FAILED", { provider_status: response.status });
    return json({ ok: false, error: "PAYTABS_PAYMENT_REQUEST_FAILED" }, 502, requestOrigin, allowedOrigin);
  }

  await env.BRAIN_DB.prepare(
    "INSERT INTO payments (tran_ref, order_id, amount, currency, provider, state, raw_evidence) VALUES (?, ?, ?, ?, 'paytabs', 'PAYMENT_PENDING', ?)"
  ).bind(String(result.tran_ref), orderId, amount, currency, JSON.stringify({
    type: "CINEMA_PAYMENT_REQUEST", tran_ref: result.tran_ref, film_id: filmId, created_at: new Date().toISOString()
  })).run();
  await env.BRAIN_DB.prepare("UPDATE orders SET state = 'PAYMENT_PENDING' WHERE order_id = ?").bind(orderId).run();
  await recordOrderEvent(env, orderId, "NEW", "PAYMENT_PENDING", "CINEMA_PAYMENT_REQUEST_CREATED", { tran_ref: result.tran_ref });

  return json({ ok: true, order_id: orderId, state: "PAYMENT_PENDING", checkout_url: result.redirect_url }, 200, requestOrigin, allowedOrigin);
}

async function cinemaAccess(request, env, requestOrigin, allowedOrigin) {
  if (!env.BRAIN_DB) return json({ ok: false, error: "D1_NOT_CONFIGURED" }, 503, requestOrigin, allowedOrigin);
  const url = new URL(request.url);
  const token = String(url.searchParams.get("token") || "").trim();
  const filmId = String(url.searchParams.get("film_id") || "").trim();
  if (!token || filmId !== "brain-last-light-city") return json({ ok: false, error: "ACCESS_TOKEN_REQUIRED" }, 401, requestOrigin, allowedOrigin);

  const tokenHash = await sha256Hex(new TextEncoder().encode(token));
  const entitlement = await env.BRAIN_DB.prepare(
    "SELECT e.order_id, e.film_id, e.state, o.state AS order_state FROM cinema_entitlements e JOIN orders o ON o.order_id=e.order_id WHERE e.token_hash=? AND e.film_id=? LIMIT 1"
  ).bind(tokenHash, filmId).first();
  if (!entitlement) return json({ ok: false, access_granted: false, error: "ENTITLEMENT_NOT_FOUND" }, 404, requestOrigin, allowedOrigin);
  if (entitlement.state !== "GRANTED" || entitlement.order_state !== "PAYMENT_VERIFIED") {
    return json({ ok: true, access_granted: false, state: entitlement.order_state || "PENDING" }, 200, requestOrigin, allowedOrigin);
  }

  const cookie = "BRAIN_CINEMA_TOKEN=" + encodeURIComponent(token) + "; Path=/; Max-Age=2592000; Secure; HttpOnly; SameSite=None";
  const headers = { "set-cookie": cookie };
  return jsonWithHeaders({ ok: true, access_granted: true, state: "ENTITLEMENT_GRANTED", stream_url: new URL("/api/cinema/stream?film_id=" + encodeURIComponent(filmId), request.url).toString() }, 200, requestOrigin, allowedOrigin, headers);
}

async function cinemaStream(request, env, requestOrigin, allowedOrigin) {
  if (!env.CINEMA_MEDIA) return json({ ok: false, error: "CINEMA_MEDIA_NOT_CONFIGURED" }, 503, requestOrigin, allowedOrigin);
  const url = new URL(request.url);
  const filmId = String(url.searchParams.get("film_id") || "").trim();
  if (filmId !== "brain-last-light-city") return json({ ok: false, error: "FILM_NOT_FOUND" }, 404, requestOrigin, allowedOrigin);

  const cookieHeader = String(request.headers.get("Cookie") || "");
  const cookieMatch = cookieHeader.match(/(?:^|;\\s*)BRAIN_CINEMA_TOKEN=([^;]+)/);
  const token = cookieMatch ? decodeURIComponent(cookieMatch[1]) : "";
  if (!token) return json({ ok: false, error: "ENTITLEMENT_REQUIRED" }, 401, requestOrigin, allowedOrigin);
  const tokenHash = await sha256Hex(new TextEncoder().encode(token));
  const entitlement = await env.BRAIN_DB?.prepare(
    "SELECT e.state, o.state AS order_state FROM cinema_entitlements e JOIN orders o ON o.order_id=e.order_id WHERE e.token_hash=? AND e.film_id=? LIMIT 1"
  ).bind(tokenHash, filmId).first();
  if (!entitlement || entitlement.state !== "GRANTED" || entitlement.order_state !== "PAYMENT_VERIFIED") {
    return json({ ok: false, error: "ENTITLEMENT_REQUIRED" }, 403, requestOrigin, allowedOrigin);
  }

  const object = await env.CINEMA_MEDIA.get("films/last_light_city.mp4", { range: request.headers });
  if (!object) return json({ ok: false, error: "CINEMA_MASTER_NOT_FOUND" }, 404, requestOrigin, allowedOrigin);
  const headers = new Headers();
  object.writeHttpMetadata(headers);
  headers.set("etag", object.httpEtag);
  headers.set("cache-control", "private, no-store");
  headers.set("accept-ranges", "bytes");
  if (object.range) {
    const range = object.range;
    if (typeof range.offset === "number" && typeof range.length === "number") {
      headers.set("content-range", "bytes " + range.offset + "-" + (range.offset + range.length - 1) + "/" + object.size);
      headers.set("content-length", String(range.length));
    }
  } else {
    headers.set("content-length", String(object.size));
  }
  headers.set("content-type", "video/mp4");
  const status = object.range ? 206 : 200;
  return new Response(object.body, { status, headers: { ...Object.fromEntries(headers), ...corsHeaders(requestOrigin, allowedOrigin) } });
}

async function createCommercialOrder(request, env, requestOrigin, allowedOrigin) {
  if (!env.BRAIN_DB) return json({ ok: false, error: "D1_NOT_CONFIGURED" }, 503, requestOrigin, allowedOrigin);
  let body;
  try { body = await request.json(); } catch { return json({ ok: false, error: "INVALID_JSON" }, 400, requestOrigin, allowedOrigin); }

  const client = await requireClient(request, env);
  if (!client.ok) return json({ ok: false, error: client.error }, client.status, requestOrigin, allowedOrigin);
  const service = String(body.service || "").trim();
  const plan = String(body.plan || "").trim();
  const need = String(body.need || "").trim();
  const prices = { "STARTER": 49, "GROWTH": 149, "CAMPAIGN": 299 };
  const key = plan.toUpperCase();
  if (!service || !need || need.length < 10) return json({ ok: false, error: "SERVICE_AND_NEED_REQUIRED" }, 400, requestOrigin, allowedOrigin);
  if (!(key in prices)) return json({ ok: false, error: "PAID_PLAN_REQUIRED" }, 400, requestOrigin, allowedOrigin);

  const orderId = "BRAIN-MKT-" + new Date().toISOString().slice(0,10).replaceAll("-","") + "-" + crypto.randomUUID().slice(0,8).toUpperCase();
  const amount = prices[key];
  await env.BRAIN_DB.prepare(
    "INSERT INTO orders (order_id, service, plan, amount, currency, state, client_email) VALUES (?, ?, ?, ?, 'USD', 'NEW', ?)"
  ).bind(orderId, service, key, amount, client.email).run();
  await recordOrderEvent(env, orderId, null, "NEW", "ORDER_CREATED", { client_email: client.email, service, plan: key, amount, currency: "USD" });

  return json({
    ok: true,
    order: { order_id: orderId, service, plan: key, amount, currency: "USD", state: "NEW", payment_state: "PAYMENT_PENDING" }
  }, 201, requestOrigin, allowedOrigin);
}

async function createPayTabsPayment(request, env, url, requestOrigin, allowedOrigin) {
  if (!env.BRAIN_DB) return json({ ok: false, error: "D1_NOT_CONFIGURED" }, 503, requestOrigin, allowedOrigin);
  const serverKey = String(env.PAYTABS_SERVER_KEY || "");
  const profileId = String(env.PAYTABS_PROFILE_ID || "");
  if (!serverKey || !profileId) return json({ ok: false, error: "PAYTABS_SECRETS_NOT_CONFIGURED" }, 503, requestOrigin, allowedOrigin);

  let body;
  try { body = await request.json(); } catch { return json({ ok: false, error: "INVALID_JSON" }, 400, requestOrigin, allowedOrigin); }

  const client = await requireClient(request, env);
  if (!client.ok) return json({ ok: false, error: client.error }, client.status, requestOrigin, allowedOrigin);
  const orderId = String(body.order_id || "").trim();
  if (!orderId) return json({ ok: false, error: "ORDER_ID_REQUIRED" }, 400, requestOrigin, allowedOrigin);

  const order = await env.BRAIN_DB.prepare(
    "SELECT order_id, service, plan, amount, currency, state, client_email FROM orders WHERE order_id = ?"
  ).bind(orderId).first();

  if (!order) return json({ ok: false, error: "ORDER_NOT_FOUND" }, 404, requestOrigin, allowedOrigin);
  if (String(order.client_email || "").toLowerCase() !== client.email.toLowerCase()) return json({ ok: false, error: "ORDER_ACCESS_DENIED" }, 403, requestOrigin, allowedOrigin);
  if (String(order.state) === "PAYMENT_VERIFIED") return json({ ok: false, error: "ORDER_ALREADY_PAID" }, 409, requestOrigin, allowedOrigin);
  if (Number(order.amount) <= 0) return json({ ok: false, error: "INVALID_ORDER_AMOUNT" }, 409, requestOrigin, allowedOrigin);

  const existing = await env.BRAIN_DB.prepare(
    "SELECT tran_ref, state FROM payments WHERE order_id = ? AND provider = 'paytabs' ORDER BY created_at DESC LIMIT 1"
  ).bind(orderId).first();
  if (existing && existing.state === "PAYMENT_VERIFIED") return json({ ok: false, error: "PAYMENT_ALREADY_VERIFIED" }, 409, requestOrigin, allowedOrigin);

  const callback = url.origin + "/api/payments/paytabs/callback";
  const returnUrl = url.origin + "/api/payments/paytabs/return";

  const payload = {
    profile_id: Number(profileId),
    tran_type: "sale",
    tran_class: "ecom",
    cart_id: order.order_id,
    cart_currency: order.currency,
    cart_amount: Number(order.amount),
    cart_description: `BRAIN ${order.service} - ${order.plan}`,
    callback,
    return: returnUrl,
  };

  const response = await fetch(PAYTABS_BASE_URL + "/payment/request", {
    method: "POST",
    headers: { Authorization: serverKey, "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const result = await response.json().catch(() => ({}));
  if (!response.ok || !result.tran_ref) {
    return json({ ok: false, error: "PAYTABS_PAYMENT_REQUEST_FAILED", provider_status: response.status }, 502, requestOrigin, allowedOrigin);
  }

  await env.BRAIN_DB.prepare(
    "INSERT OR REPLACE INTO payments (tran_ref, order_id, amount, currency, provider, state, raw_evidence) VALUES (?, ?, ?, ?, 'paytabs', 'PAYMENT_PENDING', ?)"
  ).bind(String(result.tran_ref), order.order_id, Number(order.amount), order.currency, JSON.stringify({
    type: "PAYMENT_REQUEST",
    tran_ref: result.tran_ref,
    redirect_url: result.redirect_url || null,
    created_at: new Date().toISOString(),
  })).run();

  await env.BRAIN_DB.prepare(
    "UPDATE orders SET state = 'PAYMENT_PENDING' WHERE order_id = ?"
  ).bind(order.order_id).run();
  await recordOrderEvent(env, order.order_id, String(order.state), "PAYMENT_PENDING", "PAYMENT_REQUEST_CREATED", { tran_ref: result.tran_ref });

  return json({
    ok: true,
    state: "PAYMENT_PENDING",
    order_id: order.order_id,
    tran_ref: result.tran_ref,
    redirect_url: result.redirect_url || null,
  }, 200, requestOrigin, allowedOrigin);
}


async function handlePayTabsReturn(request, env, allowedOrigin) {
  const serverKey = String(env.PAYTABS_SERVER_KEY || "");
  if (!serverKey) return new Response("Payment return verification unavailable", { status: 503 });
  const form = await request.formData();
  const fields = {};
  for (const [key, value] of form.entries()) {
    if (key !== "signature") fields[key] = String(value);
  }
  const signature = String(form.get("signature") || "").toLowerCase();
  if (!signature) return new Response("Invalid payment return", { status: 400 });
  const sorted = Object.keys(fields).filter(k => fields[k] !== "").sort().map(k => encodeURIComponent(k) + "=" + encodeURIComponent(fields[k])).join("&");
  const expected = await hmacSha256Hex(new TextEncoder().encode(sorted), serverKey);
  if (!timingSafeEqual(expected, signature)) return new Response("Invalid payment return signature", { status: 400 });
  const orderId = String(fields.cartId || "");
  const tranRef = String(fields.tranRef || "");
  const status = String(fields.respStatus || "");
  const target = new URL(String(env.BRAIN_RETURN_PAGE || allowedOrigin));
  target.searchParams.set("payment", status === "A" ? "return_received" : "return_failed");
  if (orderId) target.searchParams.set("order", orderId);
  if (tranRef) target.searchParams.set("tran_ref", tranRef);
  const cinemaToken = new URL(request.url).searchParams.get("cinema_token");
  if (cinemaToken) target.searchParams.set("cinema_token", cinemaToken);
  return Response.redirect(target.toString(), 303);
}

async function handlePayTabsCallback(request, env, requestOrigin, allowedOrigin) {
  if (!env.BRAIN_DB) return json({ ok: false, error: "D1_NOT_CONFIGURED" }, 503, requestOrigin, allowedOrigin);
  const serverKey = String(env.PAYTABS_SERVER_KEY || "");
  if (!serverKey) return json({ ok: false, error: "PAYTABS_SERVER_KEY_NOT_CONFIGURED" }, 503, requestOrigin, allowedOrigin);

  const raw = await request.arrayBuffer();
  const signature = String(request.headers.get("Signature") || "").trim().toLowerCase();
  if (!signature) return json({ ok: false, error: "SIGNATURE_REQUIRED" }, 401, requestOrigin, allowedOrigin);

  const expected = await hmacSha256Hex(raw, serverKey);
  if (!timingSafeEqual(expected, signature)) return json({ ok: false, error: "INVALID_SIGNATURE" }, 401, requestOrigin, allowedOrigin);

  let payload;
  try { payload = JSON.parse(new TextDecoder().decode(raw)); } catch { return json({ ok: false, error: "INVALID_JSON" }, 400, requestOrigin, allowedOrigin); }

  const orderId = String(payload.cart_id || "");
  const tranRef = String(payload.tran_ref || "");
  const amount = Number(payload.cart_amount);
  const currency = String(payload.cart_currency || "");
  const status = String((payload.payment_result || {}).response_status || "");

  if (!orderId || !tranRef) return json({ ok: false, error: "PAYMENT_IDENTIFIERS_MISSING" }, 400, requestOrigin, allowedOrigin);

  const payment = await env.BRAIN_DB.prepare(
    "SELECT tran_ref, order_id, amount, currency, state FROM payments WHERE tran_ref = ? AND order_id = ? AND provider = 'paytabs'"
  ).bind(tranRef, orderId).first();

  if (!payment) return json({ ok: false, error: "PAYMENT_NOT_FOUND" }, 404, requestOrigin, allowedOrigin);
  if (payment.state === "PAYMENT_VERIFIED") {
    return json({ ok: true, state: "PAYMENT_VERIFIED", tran_ref: tranRef, idempotent: true }, 200, requestOrigin, allowedOrigin);
  }
  if (Number(payment.amount) !== amount || String(payment.currency) !== currency) {
    return json({ ok: false, error: "PAYMENT_AMOUNT_OR_CURRENCY_MISMATCH" }, 409, requestOrigin, allowedOrigin);
  }

  const eventId = await sha256Hex(new TextEncoder().encode(tranRef + ":" + new TextDecoder().decode(raw)));
  const evidence = JSON.stringify({ provider: "paytabs", tran_ref: tranRef, order_id: orderId, received_at: new Date().toISOString(), payload });

  await env.BRAIN_DB.prepare(
    "INSERT OR IGNORE INTO payment_events (event_id, order_id, tran_ref, event_type, evidence) VALUES (?, ?, ?, ?, ?)"
  ).bind(eventId, orderId, tranRef, status === "A" ? "PAYMENT_VERIFIED" : "PAYMENT_REJECTED", evidence).run();

  if (status !== "A") {
    await env.BRAIN_DB.prepare("UPDATE payments SET state = 'PAYMENT_FAILED', raw_evidence = ? WHERE tran_ref = ?")
      .bind(evidence, tranRef).run();
    return json({ ok: true, state: "PAYMENT_FAILED", tran_ref: tranRef }, 200, requestOrigin, allowedOrigin);
  }

  await env.BRAIN_DB.batch([
    env.BRAIN_DB.prepare("UPDATE payments SET state = 'PAYMENT_VERIFIED', verified_at = CURRENT_TIMESTAMP, raw_evidence = ? WHERE tran_ref = ?").bind(evidence, tranRef),
    env.BRAIN_DB.prepare("UPDATE orders SET state = 'PAYMENT_VERIFIED' WHERE order_id = ?").bind(orderId),
    env.BRAIN_DB.prepare("UPDATE cinema_entitlements SET state = 'GRANTED', granted_at = CURRENT_TIMESTAMP WHERE order_id = ?").bind(orderId),
  ]);
  const revenueId = "REV-" + crypto.randomUUID().toUpperCase();
  await env.BRAIN_DB.prepare(
    "INSERT OR IGNORE INTO revenue_ledger (revenue_id, order_id, tran_ref, amount, currency, state, evidence) VALUES (?, ?, ?, ?, ?, 'REVENUE_REALIZED', ?)"
  ).bind(revenueId, orderId, tranRef, amount, currency, evidence).run();
  await recordOrderEvent(env, orderId, "PAYMENT_PENDING", "PAYMENT_VERIFIED", "PAYMENT_WEBHOOK_VERIFIED", { tran_ref: tranRef, revenue_state: "REVENUE_REALIZED", revenue_id: revenueId });

  return json({ ok: true, state: "PAYMENT_VERIFIED", tran_ref: tranRef }, 200, requestOrigin, allowedOrigin);
}


async function recordOrderEvent(env, orderId, fromState, toState, eventType, evidence) {
  if (!env.BRAIN_DB) return;
  const eventId = await sha256Hex(new TextEncoder().encode(orderId + ":" + (fromState || "") + ":" + toState + ":" + eventType + ":" + JSON.stringify(evidence)));
  await env.BRAIN_DB.prepare(
    "INSERT OR IGNORE INTO order_events (event_id, order_id, from_state, to_state, event_type, evidence) VALUES (?, ?, ?, ?, ?, ?)"
  ).bind(eventId, orderId, fromState, toState, eventType, JSON.stringify(evidence)).run();
}

async function listClientOrders(request, env, requestOrigin, allowedOrigin) {
  if (!env.BRAIN_DB) return json({ ok: false, error: "D1_NOT_CONFIGURED" }, 503, requestOrigin, allowedOrigin);
  const client = await requireClient(request, env);
  if (!client.ok) return json({ ok: false, error: client.error }, client.status, requestOrigin, allowedOrigin);
  const result = await env.BRAIN_DB.prepare(
    "SELECT order_id, service, plan, amount, currency, state, created_at FROM orders WHERE client_email = ? ORDER BY created_at DESC LIMIT 50"
  ).bind(client.email).all();
  return json({ ok: true, orders: result.results || [] }, 200, requestOrigin, allowedOrigin);
}

async function requireClient(request, env) {
  const auth = String(request.headers.get("Authorization") || "");
  if (!auth.startsWith("Bearer ")) return { ok: false, status: 401, error: "AUTH_REQUIRED" };
  const origin = String(env.BRAIN_ORIGIN || "").replace(/\/$/, "");
  if (!origin || origin.includes("REPLACE_WITH_")) return { ok: false, status: 503, error: "CLIENT_AUTH_ORIGIN_NOT_CONFIGURED" };
  try {
    const response = await fetch(origin + "/auth/me", { headers: { Authorization: auth, Accept: "application/json" } });
    if (!response.ok) return { ok: false, status: 401, error: "INVALID_CLIENT_SESSION" };
    const data = await response.json();
    const email = String((data.account || {}).email || "").trim();
    if (!email) return { ok: false, status: 401, error: "CLIENT_IDENTITY_MISSING" };
    return { ok: true, email };
  } catch {
    return { ok: false, status: 502, error: "CLIENT_AUTH_UNAVAILABLE" };
  }
}

async function hmacSha256Hex(data, secret) {
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const sig = await crypto.subtle.sign("HMAC", key, data);
  return [...new Uint8Array(sig)].map(b => b.toString(16).padStart(2, "0")).join("");
}

async function sha256Hex(data) {
  const digest = await crypto.subtle.digest("SHA-256", data);
  return [...new Uint8Array(digest)].map(b => b.toString(16).padStart(2, "0")).join("");
}

function timingSafeEqual(a, b) {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

function corsHeaders(requestOrigin = "", allowedOrigin = DEFAULT_ALLOWED_ORIGIN) {
  return {
    "access-control-allow-origin": allowedOrigin,
    "access-control-allow-methods": "GET,POST,PUT,PATCH,DELETE,OPTIONS",
    "access-control-allow-headers": "Content-Type, Authorization, X-V12-Agent-Key, Signature",
    "access-control-allow-credentials": "true",
  };
}


function jsonWithHeaders(value, status, requestOrigin, allowedOrigin, extraHeaders = {}) {
  return new Response(JSON.stringify(value), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", ...corsHeaders(requestOrigin, allowedOrigin), ...extraHeaders },
  });
}

function json(value, status = 200, requestOrigin = "", allowedOrigin = DEFAULT_ALLOWED_ORIGIN) {
  return new Response(JSON.stringify(value), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", ...corsHeaders(requestOrigin, allowedOrigin) },
  });
}
