import assert from "node:assert/strict";
import worker from "../src/index.js";

const calls = [];
const db = {
  prepare(sql) {
    return { sql, values: [], bind(...values) { this.values = values; return this; },
      async first() {
        calls.push({kind:"first",sql:this.sql,values:this.values});
        if (this.sql.includes("FROM deliveries d JOIN orders")) return {delivery_id:"D1",order_id:"O1",state:"READY"};
        if (this.sql.includes("FROM payments WHERE order_id")) return {tran_ref:"T1",amount:9,currency:"JOD",state:"PAYMENT_VERIFIED"};
        return null;
      },
      async run() { calls.push({kind:"run",sql:this.sql,values:this.values}); return {success:true,meta:{changes:1}}; },
      async all() { return {results:[]}; }
    };
  },
  async batch(items) { const out=[]; for (const item of items) out.push(await item.run()); return out; }
};
const originalFetch = globalThis.fetch;
globalThis.fetch = async () => new Response(JSON.stringify({account:{email:"buyer@example.test"}}), {status:200,headers:{"Content-Type":"application/json"}});
try {
  const response = await worker.fetch(new Request("https://test.invalid/api/deliveries/confirm", {
    method:"POST", headers:{"Content-Type":"application/json",Authorization:"Bearer test-session"},
    body:JSON.stringify({delivery_id:"D1"})
  }), {BRAIN_DB:db,BRAIN_ORIGIN:"https://auth.invalid",BRAIN_ALLOWED_ORIGIN:"https://test.invalid"});
  assert.equal(response.status,200);
  assert.equal((await response.json()).state,"DELIVERED");
  const deliveryUpdate=calls.find(x=>x.sql.includes("UPDATE deliveries SET state = 'DELIVERED'"));
  const orderUpdate=calls.find(x=>x.sql.includes("UPDATE orders SET state = 'COMPLETED'"));
  const revenueUpdate=calls.find(x=>x.sql.includes("UPDATE revenue_ledger SET state = 'REVENUE_REALIZED'"));
  assert.ok(deliveryUpdate,"delivery is marked delivered");
  assert.ok(orderUpdate,"order completion is attempted");
  assert.ok(revenueUpdate,"revenue realization is attempted only after verified payment lookup");
  assert.equal(revenueUpdate.values[1],"O1");
  assert.equal(revenueUpdate.values[2],"T1");
  assert.equal(revenueUpdate.values[3],9);
  assert.equal(revenueUpdate.values[4],"JOD");
  assert.ok(calls.some(x=>x.sql.includes("CLIENT_DELIVERY_CONFIRMED")),"delivery audit event is written");
  console.log("DYNAMIC_DELIVERY_HANDLER=PASS");
  console.log("VERIFIED_PAYMENT_AND_AMOUNT_CURRENCY_SCOPING=PASS");
  console.log("DELIVERY_AUDIT_EVENT=PASS");
  console.log("LIMITATION=mock D1 adapter; not Cloudflare D1 integration");
} finally { globalThis.fetch = originalFetch; }
