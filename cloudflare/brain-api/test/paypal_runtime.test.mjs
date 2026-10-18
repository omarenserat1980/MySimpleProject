import test from "node:test";
import assert from "node:assert/strict";
import worker from "../src/index.js";

async function post(path, env = {}, body = {}) {
  return worker.fetch(new Request("https://brain.test" + path, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  }), env);
}

test("PayPal create fails closed when D1 is not configured", async () => {
  const response = await post("/api/payments/paypal/create");
  assert.equal(response.status, 503);
  assert.deepEqual(await response.json(), { ok: false, error: "D1_NOT_CONFIGURED" });
});

test("PayPal capture fails closed when D1 is not configured", async () => {
  const response = await post("/api/payments/paypal/capture");
  assert.equal(response.status, 503);
  assert.deepEqual(await response.json(), { ok: false, error: "D1_NOT_CONFIGURED" });
});

test("PayPal webhook fails closed when D1 is not configured", async () => {
  const response = await post("/api/payments/paypal/webhook");
  assert.equal(response.status, 503);
  assert.deepEqual(await response.json(), { ok: false, error: "D1_NOT_CONFIGURED" });
});

test("PayPal webhook requires configured webhook identity before provider verification", async () => {
  const response = await post("/api/payments/paypal/webhook", { BRAIN_DB: {} });
  assert.equal(response.status, 503);
  assert.deepEqual(await response.json(), { ok: false, error: "PAYPAL_WEBHOOK_ID_NOT_CONFIGURED" });
});

test("health reports missing delivery artifact policy rather than claiming readiness", async () => {
  const response = await worker.fetch(new Request("https://brain.test/health"), {});
  assert.equal(response.status, 200);
  const body = await response.json();
  assert.equal(body.d1, "NOT_CONFIGURED");
  assert.equal(body.delivery_artifact_policy, "NOT_CONFIGURED");
});

test("PayPal create requires an authenticated client session", async () => {
  const response = await post("/api/payments/paypal/create", { BRAIN_DB: {} }, { order_id: "order-test" });
  assert.equal(response.status, 401);
  assert.deepEqual(await response.json(), { ok: false, error: "AUTH_REQUIRED" });
});

test("PayPal capture requires an authenticated client session", async () => {
  const response = await post("/api/payments/paypal/capture", { BRAIN_DB: {} }, { order_id: "order-test", paypal_order_id: "paypal-test" });
  assert.equal(response.status, 401);
  assert.deepEqual(await response.json(), { ok: false, error: "AUTH_REQUIRED" });
});

test("PayPal create fails closed when client identity provider is not configured", async () => {
  const response = await worker.fetch(new Request("https://brain.test/api/payments/paypal/create", {
    method: "POST",
    headers: { "content-type": "application/json", "authorization": "Bearer synthetic-test-token" },
    body: JSON.stringify({ order_id: "order-test" }),
  }), { BRAIN_DB: {}, BRAIN_ORIGIN: "" });
  assert.equal(response.status, 503);
  assert.deepEqual(await response.json(), { ok: false, error: "CLIENT_AUTH_ORIGIN_NOT_CONFIGURED" });
});


test("PayPal webhook rejects malformed JSON before attempting provider authentication", async () => {
  const response = await worker.fetch(new Request("https://brain.test/api/payments/paypal/webhook", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: "{not-json",
  }), { BRAIN_DB: {}, PAYPAL_WEBHOOK_ID: "synthetic-webhook-id" });
  assert.equal(response.status, 400);
  assert.deepEqual(await response.json(), { ok: false, error: "INVALID_JSON" });
});


test("PayPal webhook rejects missing signature headers before OAuth credentials or provider calls", async () => {
  const response = await post("/api/payments/paypal/webhook", {
    BRAIN_DB: {},
    PAYPAL_WEBHOOK_ID: "synthetic-webhook-id",
  }, { event_type: "PAYMENT.CAPTURE.COMPLETED" });
  assert.equal(response.status, 401);
  assert.deepEqual(await response.json(), { ok: false, error: "PAYPAL_WEBHOOK_HEADERS_REQUIRED" });
});


test("PayPal webhook fails closed without OAuth credentials after envelope validation", async () => {
  const response = await worker.fetch(new Request("https://brain.test/api/payments/paypal/webhook", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "PAYPAL-AUTH-ALGO": "SHA256withRSA",
      "PAYPAL-CERT-URL": "https://example.invalid/cert",
      "PAYPAL-TRANSMISSION-ID": "synthetic-transmission-id",
      "PAYPAL-TRANSMISSION-SIG": "synthetic-signature",
      "PAYPAL-TRANSMISSION-TIME": "2026-10-18T00:00:00Z",
    },
    body: JSON.stringify({ event_type: "PAYMENT.CAPTURE.COMPLETED", resource: { status: "COMPLETED" } }),
  }), { BRAIN_DB: {}, PAYPAL_WEBHOOK_ID: "synthetic-webhook-id" });
  assert.equal(response.status, 503);
  assert.deepEqual(await response.json(), { ok: false, error: "PAYPAL_SECRETS_NOT_CONFIGURED" });
});


test("verified PayPal capture retry repairs ledger and service job without another provider call", async () => {
  const sqlCalls = [];
  const evidence = JSON.stringify({
    provider: "paypal",
    event: "CAPTURE_COMPLETED",
    paypal_order_id: "PP-ORDER-1",
    capture_id: "PP-CAPTURE-1",
    amount: 12.5,
    currency: "JOD",
    status: "COMPLETED",
  });
  const payment = {
    tran_ref: "PP-ORDER-1",
    order_id: "ORDER-1",
    amount: 12.5,
    currency: "JOD",
    state: "PAYMENT_VERIFIED",
    raw_evidence: evidence,
  };
  const order = {
    order_id: "ORDER-1",
    amount: 12.5,
    currency: "JOD",
    state: "PAYMENT_VERIFIED",
    client_email: "buyer@example.test",
  };
  const db = {
    prepare(sql) {
      return {
        sql,
        values: [],
        bind(...values) { this.values = values; return this; },
        async first() {
          sqlCalls.push({ kind: "first", sql: this.sql, values: this.values });
          if (this.sql.includes("FROM orders WHERE order_id = ?")) return order;
          if (this.sql.includes("FROM payments WHERE tran_ref = ?")) return payment;
          if (this.sql.includes("FROM revenue_ledger WHERE order_id = ?")) {
            return { tran_ref: "PP-ORDER-1", amount: 12.5, currency: "JOD", state: "PAYMENT_VERIFIED_PENDING_DELIVERY" };
          }
          if (this.sql.includes("FROM service_jobs WHERE job_id = ?")) {
            return { job_id: this.values[0], state: "PENDING" };
          }
          return null;
        },
        async run() {
          sqlCalls.push({ kind: "run", sql: this.sql, values: this.values });
          return { success: true, meta: { changes: 1 } };
        },
      };
    },
    async batch(statements) {
      sqlCalls.push({ kind: "batch", count: statements.length });
      return Promise.all(statements.map(statement => statement.run()));
    },
  };

  const originalFetch = globalThis.fetch;
  const providerCalls = [];
  globalThis.fetch = async (url, init = {}) => {
    if (String(url) === "https://auth.test/auth/me") {
      return new Response(JSON.stringify({ account: { email: "buyer@example.test" } }), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    }
    providerCalls.push(String(url));
    throw new Error("unexpected external provider call during verified retry");
  };

  try {
    const response = await worker.fetch(new Request("https://brain.test/api/payments/paypal/capture", {
      method: "POST",
      headers: {
        "content-type": "application/json",
        authorization: "Bearer synthetic-session",
      },
      body: JSON.stringify({ order_id: "ORDER-1", paypal_order_id: "PP-ORDER-1" }),
    }), {
      BRAIN_DB: db,
      BRAIN_ORIGIN: "https://auth.test",
      BRAIN_ALLOWED_ORIGIN: "https://brain.test",
    });

    assert.equal(response.status, 200);
    const body = await response.json();
    assert.equal(body.state, "PAYMENT_VERIFIED_PENDING_DELIVERY");
    assert.equal(body.capture_id, "PP-CAPTURE-1");
    assert.equal(body.idempotent, true);
    const batch = sqlCalls.find(call => call.kind === "batch");
    assert.ok(batch, "verified retry must run the atomic recovery batch");
    assert.equal(batch.count, 5, "recovery batch must persist event, payment/order state, ledger and service job");
    assert.ok(sqlCalls.some(call => call.sql?.includes("INSERT OR IGNORE INTO revenue_ledger")));
    assert.ok(sqlCalls.some(call => call.sql?.includes("INSERT OR IGNORE INTO service_jobs")));
    assert.deepEqual(providerCalls, [], "verified retry must not call PayPal again");
  } finally {
    globalThis.fetch = originalFetch;
  }
});


test("verified PayPal retry rebuilds both missing ledger and service-job rows", async () => {
  const payment = {
    tran_ref: "PP-ORDER-REPAIR",
    order_id: "ORDER-REPAIR",
    amount: 7.25,
    currency: "JOD",
    state: "PAYMENT_VERIFIED",
    raw_evidence: JSON.stringify({
      provider: "paypal",
      capture_id: "PP-CAPTURE-REPAIR",
      amount: 7.25,
      currency: "JOD",
      status: "COMPLETED",
    }),
  };
  const order = {
    order_id: "ORDER-REPAIR",
    amount: 7.25,
    currency: "JOD",
    state: "PAYMENT_VERIFIED",
    client_email: "repair@example.test",
  };
  let ledger = null;
  let job = null;
  const batchSql = [];
  const db = {
    prepare(sql) {
      return {
        sql,
        values: [],
        bind(...values) { this.values = values; return this; },
        async first() {
          if (this.sql.includes("FROM orders WHERE order_id = ?")) return order;
          if (this.sql.includes("FROM payments WHERE tran_ref = ?")) return payment;
          if (this.sql.includes("FROM revenue_ledger WHERE order_id = ?")) return ledger;
          if (this.sql.includes("FROM service_jobs WHERE job_id = ?")) return job;
          return null;
        },
        async run() {
          batchSql.push(this.sql);
          if (this.sql.includes("INSERT OR IGNORE INTO revenue_ledger")) {
            ledger = {
              revenue_id: this.values[0],
              order_id: this.values[1],
              tran_ref: this.values[2],
              amount: this.values[3],
              currency: this.values[4],
              state: "PAYMENT_VERIFIED_PENDING_DELIVERY",
            };
          }
          if (this.sql.includes("INSERT OR IGNORE INTO service_jobs")) {
            job = {
              job_id: this.values[0],
              order_id: this.values[1],
              state: "PENDING",
            };
          }
          return { success: true, meta: { changes: 1 } };
        },
      };
    },
    async batch(statements) {
      for (const statement of statements) await statement.run();
      return [];
    },
  };

  const originalFetch = globalThis.fetch;
  globalThis.fetch = async url => {
    if (String(url) === "https://auth.test/auth/me") {
      return new Response(JSON.stringify({ account: { email: "repair@example.test" } }), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    }
    throw new Error("unexpected provider call for verified retry");
  };

  try {
    const response = await worker.fetch(new Request("https://brain.test/api/payments/paypal/capture", {
      method: "POST",
      headers: { "content-type": "application/json", authorization: "Bearer synthetic-session" },
      body: JSON.stringify({ order_id: "ORDER-REPAIR", paypal_order_id: "PP-ORDER-REPAIR" }),
    }), {
      BRAIN_DB: db,
      BRAIN_ORIGIN: "https://auth.test",
      BRAIN_ALLOWED_ORIGIN: "https://brain.test",
    });

    assert.equal(response.status, 200);
    const result = await response.json();
    assert.equal(result.idempotent, true);
    assert.equal(result.capture_id, "PP-CAPTURE-REPAIR");
    assert.equal(ledger?.tran_ref, "PP-ORDER-REPAIR", "missing ledger row must be recreated");
    assert.equal(ledger?.amount, 7.25);
    assert.equal(job?.order_id, "ORDER-REPAIR", "missing service job must be recreated");
    assert.ok(batchSql.some(sql => sql.includes("INSERT OR IGNORE INTO revenue_ledger")));
    assert.ok(batchSql.some(sql => sql.includes("INSERT OR IGNORE INTO service_jobs")));
  } finally {
    globalThis.fetch = originalFetch;
  }
});


test("verified PayPal retry rejects incomplete persisted capture evidence without repairing or calling provider", async () => {
  const order = {
    order_id: "ORDER-BROKEN-EVIDENCE",
    amount: 4.5,
    currency: "JOD",
    state: "PAYMENT_VERIFIED",
    client_email: "buyer@example.test",
  };
  const payment = {
    tran_ref: "PP-BROKEN-EVIDENCE",
    order_id: "ORDER-BROKEN-EVIDENCE",
    amount: 4.5,
    currency: "JOD",
    state: "PAYMENT_VERIFIED",
    raw_evidence: JSON.stringify({ provider: "paypal", status: "COMPLETED" }),
  };
  let batchCalls = 0;
  const db = {
    prepare(sql) {
      return {
        sql,
        values: [],
        bind(...values) { this.values = values; return this; },
        async first() {
          if (this.sql.includes("FROM orders WHERE order_id = ?")) return order;
          if (this.sql.includes("FROM payments WHERE tran_ref = ?")) return payment;
          throw new Error("unexpected database read after incomplete evidence");
        },
        async run() { throw new Error("unexpected database write for incomplete evidence"); },
      };
    },
    async batch() {
      batchCalls += 1;
      throw new Error("unexpected batch for incomplete evidence");
    },
  };

  const originalFetch = globalThis.fetch;
  const providerCalls = [];
  globalThis.fetch = async url => {
    if (String(url) === "https://auth.test/auth/me") {
      return new Response(JSON.stringify({ account: { email: "buyer@example.test" } }), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    }
    providerCalls.push(String(url));
    throw new Error("PayPal provider must not be called for an already-verified payment with broken evidence");
  };

  try {
    const response = await worker.fetch(new Request("https://brain.test/api/payments/paypal/capture", {
      method: "POST",
      headers: { "content-type": "application/json", authorization: "Bearer synthetic-session" },
      body: JSON.stringify({
        order_id: "ORDER-BROKEN-EVIDENCE",
        paypal_order_id: "PP-BROKEN-EVIDENCE",
      }),
    }), {
      BRAIN_DB: db,
      BRAIN_ORIGIN: "https://auth.test",
      BRAIN_ALLOWED_ORIGIN: "https://brain.test",
    });

    assert.equal(response.status, 409);
    assert.deepEqual(await response.json(), { ok: false, error: "PAYPAL_VERIFIED_EVIDENCE_INCOMPLETE" });
    assert.equal(batchCalls, 0, "incomplete evidence must not write ledger/job records");
    assert.deepEqual(providerCalls, [], "incomplete verified retries must not call the provider");
  } finally {
    globalThis.fetch = originalFetch;
  }
});
