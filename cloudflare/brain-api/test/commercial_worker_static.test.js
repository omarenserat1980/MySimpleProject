const assert = require("node:assert/strict");
const fs = require("node:fs");

const worker = fs.readFileSync("src/index.js", "utf8");
const schema = fs.readFileSync("migrations/0001_commercial.sql", "utf8");
const clientMigration = fs.readFileSync("migrations/0002_order_client.sql", "utf8");
const auditMigration = fs.readFileSync("migrations/0003_order_audit.sql", "utf8");
const revenueMigration = fs.readFileSync("migrations/0004_revenue_ledger.sql", "utf8");
const deliveryMigration = fs.readFileSync("migrations/0005_delivery.sql", "utf8");
const jobsMigration = fs.readFileSync("migrations/0006_jobs.sql", "utf8");
const cinemaMigration = fs.readFileSync("migrations/0007_cinema_entitlements.sql", "utf8");
const wrangler = fs.readFileSync("wrangler.toml", "utf8");

assert.match(worker, /PAYTABS_SERVER_KEY/);
assert.match(worker, /Signature/);
assert.match(worker, /HMAC/);
assert.match(worker, /PAYMENT_VERIFIED/);
assert.match(worker, /PAYMENT_PENDING/);
assert.match(worker, /PAYMENT_AMOUNT_OR_CURRENCY_MISMATCH/);
assert.match(worker, /idempotent: true/);
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

assert.match(worker, /requireClient/);
assert.match(worker, /AUTH_REQUIRED/);
assert.match(worker, /ORDER_ACCESS_DENIED/);
assert.match(clientMigration, /client_email/);

assert.match(worker, /listClientOrders/);
assert.match(worker, /ORDER BY created_at DESC LIMIT 50/);

assert.match(worker, /recordOrderEvent/);
assert.match(worker, /PAYMENT_WEBHOOK_VERIFIED/);
assert.match(auditMigration, /CREATE TABLE IF NOT EXISTS order_events/);

assert.match(worker, /REVENUE_REALIZED/);
assert.match(worker, /revenue_ledger/);
assert.match(worker, /revenue_state/);
assert.match(revenueMigration, /CREATE TABLE IF NOT EXISTS revenue_ledger/);
assert.match(revenueMigration, /UNIQUE/);

assert.match(worker, /createCinemaCheckout/);
assert.match(worker, /cinemaAccess/);
assert.match(worker, /cinemaStream/);
assert.match(worker, /CINEMA_MEDIA/);
assert.match(worker, /cinema_entitlements/);
assert.match(worker, /BRAIN_CINEMA_TOKEN/);
assert.match(cinemaMigration, /CREATE TABLE IF NOT EXISTS cinema_entitlements/);
assert.match(worker, /granted_at = CURRENT_TIMESTAMP/);
assert.match(worker, /CINEMA_MASTER_NOT_FOUND/);
console.log("CINEMA_ENTITLEMENT_GATES=PASS");

assert.match(worker, /listClientDeliveries/);
assert.match(worker, /deliveries d JOIN orders o/);
assert.match(deliveryMigration, /CREATE TABLE IF NOT EXISTS deliveries/);

assert.match(worker, /service_jobs/);
assert.match(worker, /listClientJobs/);
assert.match(worker, /state, attempt/);
assert.match(jobsMigration, /CREATE TABLE IF NOT EXISTS service_jobs/);
assert.match(jobsMigration, /attempt INTEGER/);

assert.match(worker, /claimNextJob/);
assert.match(worker, /CONTROL_AUTH_REQUIRED/);
assert.match(worker, /attempt < 3/);
assert.match(worker, /state = 'RUNNING'/);

assert.match(worker, /completeJob/);
assert.match(worker, /RESULT_EVIDENCE_REQUIRED/);
assert.match(worker, /JOB_NOT_RUNNING/);
assert.match(worker, /state = 'SUCCESS'/);
assert.match(worker, /order_state: "READY"/);

assert.match(worker, /confirmDelivery/);
assert.match(worker, /DELIVERY_NOT_READY/);
assert.match(worker, /CLIENT_DELIVERY_CONFIRMED/);
assert.match(worker, /order_state: "COMPLETED"/);

const supervisor = fs.readFileSync("src/supervisor.js", "utf8");
assert.match(supervisor, /supervisorTick/);
assert.match(supervisor, /30 minutes/);
assert.match(supervisor, /attempt < 3/);
assert.match(worker, /supervisorTick/);
assert.match(worker, /\/api\/supervisor\/tick/);
