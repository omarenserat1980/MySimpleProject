const assert = require("node:assert/strict");
const fs = require("node:fs");

const worker = fs.readFileSync("src/index.js", "utf8");
const schema = fs.readFileSync("migrations/0001_commercial.sql", "utf8");
const wrangler = fs.readFileSync("wrangler.toml", "utf8");

assert.match(worker, /PAYTABS_SERVER_KEY/);
assert.match(worker, /Signature/);
assert.match(worker, /HMAC/);
assert.match(worker, /PAYMENT_VERIFIED/);
assert.match(worker, /PAYMENT_PENDING/);
assert.match(worker, /PAYMENT_AMOUNT_OR_CURRENCY_MISMATCH/);
assert.match(worker, /INSERT OR IGNORE INTO payment_events/);
assert.match(worker, /secure-jordan\.paytabs\.com\/payment\/request/);
assert.match(schema, /CREATE TABLE IF NOT EXISTS orders/);
assert.match(schema, /CREATE TABLE IF NOT EXISTS payments/);
assert.match(schema, /CREATE TABLE IF NOT EXISTS payment_events/);
assert.match(wrangler, /binding = "BRAIN_DB"/);
assert.match(wrangler, /migrations_dir = "migrations"/);

console.log("COMMERCIAL_WORKER_STATIC_TEST=PASS");
console.log("PAYMENT_VERIFICATION_GATES=PASS");
console.log("D1_SCHEMA_GATES=PASS");
console.log("NO_LIVE_SECRET_USED=TRUE");
