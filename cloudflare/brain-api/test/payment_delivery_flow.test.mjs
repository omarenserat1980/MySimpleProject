import assert from "node:assert/strict";
import worker from "../src/index.js";

const calls = [];
const db = {
  prepare(sql) {
    return {
      sql, values: [],
      bind(...values) { this.values = values; return this; },
      async first() {
        calls.push({ kind: "first", sql: this.sql, values: this.values });
        if (this.sql.includes("FROM deliveries d JOIN orders")) return { delivery_id: "D1", order_id: "O1", state: "READY" };
        if (this.sql.includes("FROM payments WHERE order_id")) return { tran_ref: "T1", amount: 9, currency: "JOD", state: "PAYMENT_VERIFIED" };
        return null;
      },
      async run() { calls.push({ kind: "run", sql: this.sql, values: this.values }); return { success: true, meta: { changes: 1 } }; },
      async all() { return { results: [] }; }
    };
  },
  async batch(items) { const results = []; for (const item of items) results.push(await item.run()); return results; }
};

const originalFetch = globalThis.fetch;
globalThis.fetch = async () => new Response(JSON.stringify({ account: { email: "buyer@example.test" } }), {
  status: 200, headers: { "Content-Type": "application/json" }
});

try {
  const response = await worker.fetch(new Request("https://test.invalid/api/deliveries/confirm", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: "Bearer test-session", Origin: "https://test.invalid" },
    body: JSON.stringify({ delivery_id: "D1" })
  }), { BRAIN_DB: db, BRAIN_ORIGIN: "https://auth.invalid", BRAIN_ALLOWED_ORIGIN: "https://test.invalid" });

  assert.equal(response.status, 200);
  const result = await response.json();
  assert.equal(result.state, "DELIVERED");
  assert.equal(result.order_state, "COMPLETED");
  assert.equal(result.revenue_realized, false);
  assert.equal(result.settlement_required, true);

  const deliveryUpdate = calls.find(x => x.sql.includes("UPDATE deliveries SET state = 'DELIVERED'"));
  const orderUpdate = calls.find(x => x.sql.includes("UPDATE orders SET state = 'COMPLETED'"));
  const ledgerUpdate = calls.find(x => x.sql.includes("UPDATE revenue_ledger SET state = 'DELIVERY_CONFIRMED_PENDING_SETTLEMENT'"));
  const eventInsert = calls.find(x => x.sql.includes("INSERT OR IGNORE INTO order_events"));
  assert.ok(deliveryUpdate, "delivery must be marked delivered");
  assert.ok(orderUpdate, "order must be marked completed");
  assert.ok(ledgerUpdate, "eligible live ledger row may advance only to pending settlement");
  assert.ok(eventInsert, "delivery confirmation event must be recorded");
  assert.match(ledgerUpdate.sql, /environment = 'live'/);
  assert.match(ledgerUpdate.sql, /amount = \?/);
  assert.match(ledgerUpdate.sql, /currency = \?/);
  assert.match(ledgerUpdate.sql, /state = 'PAYMENT_VERIFIED_PENDING_DELIVERY'/);
  assert.deepEqual(ledgerUpdate.values.slice(1), ["O1", "T1", 9, "JOD", "D1", "O1"]);
  assert.ok(!calls.some(x => x.sql.includes("UPDATE revenue_ledger SET state = 'REALIZED'")),
    "delivery alone must never realize revenue");
  console.log("PAYMENT_DELIVERY_SETTLEMENT_ORDERING=PASS");
  console.log("DELIVERY_DOES_NOT_REALIZE_REVENUE=PASS");
} finally {
  globalThis.fetch = originalFetch;
}
