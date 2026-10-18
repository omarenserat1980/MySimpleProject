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
