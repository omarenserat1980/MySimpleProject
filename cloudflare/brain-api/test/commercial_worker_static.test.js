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
const settlementMigration = fs.readFileSync("migrations/0009_settlement_reference.sql", "utf8");
const wrangler = fs.readFileSync("wrangler.toml", "utf8");

assert.match(worker, /delivery_artifact_policy/, "health must report delivery artifact policy readiness");
assert.match(worker, /deliveryOrigins\.length > 0 \? "CONFIGURED" : "NOT_CONFIGURED"/, "health readiness must reflect the artifact origin allowlist");
assert.match(worker, /PAYTABS_SERVER_KEY/);
assert.match(worker, /Signature/);
assert.match(worker, /HMAC/);
assert.match(worker, /PAYMENT_VERIFIED/);
assert.match(worker, /PAYMENT_PENDING/);
assert.match(worker, /PAYMENT_AMOUNT_OR_CURRENCY_MISMATCH/);
assert.match(worker, /PAYMENT_REQUEST_ALREADY_PENDING/, "pending checkout retries must fail closed when prior checkout evidence is incomplete");
assert.match(worker, /idempotent: true/, "pending checkout retry must reuse persisted checkout evidence");
assert.doesNotMatch(worker, /INSERT OR REPLACE INTO payments/, "payment retries must not replace existing financial evidence");
assert.match(worker, /idempotent: true/);
assert.match(worker, /INSERT OR IGNORE INTO payment_events/);
assert.match(worker, /secure-jordan\.paytabs\.com/);
assert.ok(worker.includes('PAYTABS_BASE_URL + "/payment/request"'), "PayTabs request URL contract missing");
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

const confirmDeliverySource = worker.slice(worker.indexOf("async function confirmDelivery("), worker.indexOf("async function completeJob("));
assert.doesNotMatch(confirmDeliverySource, /REVENUE_REALIZED/, "delivery confirmation must not mark revenue realized");
assert.match(worker, /async function verifySignedSettlementEvidence/);
assert.match(worker, /BRAIN_SETTLEMENT_ATTESTATION_KEY/);
assert.match(worker, /SETTLEMENT_SIGNATURE_INVALID/);
assert.match(worker, /SETTLEMENT_AMOUNT_OR_CURRENCY_MISMATCH/);
assert.match(worker, /UPDATE revenue_ledger SET state = 'REVENUE_REALIZED'/, "revenue realization transition must exist only behind settlement verification");
assert.match(worker, /PAYMENT_VERIFIED_PENDING_DELIVERY/);
assert.match(worker, /revenue_state: "PAYMENT_VERIFIED_PENDING_DELIVERY"/, "payment callback must not report revenue realized before delivery");
assert.match(worker, /Delivery is not proof of provider settlement/);
assert.match(worker, /DELIVERY_CONFIRMED_PENDING_SETTLEMENT/);
assert.doesNotMatch(confirmDeliverySource, /UPDATE revenue_ledger SET state = 'REVENUE_REALIZED'/, "delivery confirmation must not by itself recognize collected revenue");

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
assert.match(worker, /WHERE job_id = \? AND state = 'RUNNING'/, "job completion must use compare-and-set to prevent concurrent completion");
assert.match(worker, /JOB_COMPLETION_RACE/, "concurrent completion must fail closed");
assert.match(worker, /DELIVERY_PERSISTENCE_FAILED/, "completion must not claim success if delivery persistence failed");
assert.match(worker, /STRUCTURED_RESULT_EVIDENCE_REQUIRED/, "job completion must reject free-form evidence");
assert.match(worker, /HTTPS_ARTIFACT_URL_REQUIRED/, "job completion must require an HTTPS delivery artifact");
assert.match(worker, /BRAIN_DELIVERY_ALLOWED_ORIGINS/, "delivery artifacts must use an explicitly configured origin allowlist");
assert.match(worker, /ARTIFACT_ORIGIN_NOT_ALLOWED/, "unapproved delivery origins must be rejected");
assert.match(worker, /ARTIFACT_SHA256_REQUIRED/, "job completion must require a SHA-256 artifact digest");
assert.match(worker, /artifact_sha256/, "delivery evidence must bind the artifact digest");
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

assert.match(worker, /transitionClientOrder/);
assert.match(worker, /INVALID_STATE_TRANSITION/);
assert.match(worker, /PAYMENT_VERIFIED: \["IN_PROGRESS"\]/);

assert.match(worker, /PAYTABS_MODE \\|\\| "test"/, "payment mode must default safely to test");
assert.match(worker, /SANDBOX_PAYMENT_VERIFIED_PENDING_DELIVERY/, "sandbox payments must be separately classified");
assert.match(worker, /environment = 'live'/, "revenue realization must require live environment");
console.log("SANDBOX_CANNOT_REALIZE_REVENUE=PASS");


assert.match(worker, /payload\.payment_result \|\| payload/, "PayTabs callback must support top-level response_status");
assert.match(worker, /transactionType !== "sale"/, "authorization/refund callbacks must not verify a sale payment");
assert.ok(worker.indexOf("PAYMENT_AMOUNT_OR_CURRENCY_MISMATCH") < worker.indexOf('if (payment.state === "PAYMENT_VERIFIED")'), "amount/currency must be validated before idempotent success");
assert.match(worker, /revenue_realized: false/, "delivery confirmation must not claim settlement");
assert.match(worker, /settlement_required: settlementRequired/, "delivery response must surface the outstanding settlement gate");
console.log("PAYTABS_CALLBACK_AMOUNT_IDEMPOTENCY_GATES=PASS");
console.log("REVENUE_LEDGER_UPDATE_EVIDENCE_GATE=PASS");


assert.match(worker, /reconcilePayTabsTransactionQuery/, "read-only PayTabs transaction reconciliation handler must exist");
assert.match(worker, /\/api\/payments\/paytabs\/reconcile-query/, "reconciliation endpoint must be registered");
assert.match(worker, /PAYTABS_BASE_URL \+ "\/payment\/query"/, "reconciliation must use the documented PayTabs query endpoint");
assert.match(worker, /TRANSACTION_QUERY_CONFIRMED_NOT_SETTLEMENT/, "a transaction query must not be misrepresented as payout settlement");
assert.match(worker, /settlement_verified: false/, "transaction query must not claim settlement verification");
assert.match(worker, /revenue_realized: false/, "transaction query must not realize revenue");
assert.match(worker, /PAYTABS_QUERY_EVIDENCE_MISMATCH/, "transaction query must fail closed on order/amount/currency/reference mismatch");
assert.match(worker, /CONTROL_AUTH_REQUIRED/, "transaction reconciliation must require control-plane authentication");

assert.match(worker, /SETTLEMENT_REFERENCE_ALREADY_USED/, "settlement references must not be reused across revenue rows");
assert.match(worker, /settlement_reference IS NULL/, "realization transition must only happen once per ledger row");
assert.match(settlementMigration, /CREATE UNIQUE INDEX IF NOT EXISTS idx_revenue_settlement_reference_unique/, "settlement reference must be unique");
assert.match(worker, /!\/^\\\\d\{4\}-\\\\d\{2\}-\\\\d\{2\}\$\//, "settlement date must use YYYY-MM-DD validation");