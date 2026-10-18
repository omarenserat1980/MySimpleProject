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
assert.ok(confirmDeliverySource.includes("AND EXISTS (SELECT 1 FROM deliveries d JOIN orders o") && confirmDeliverySource.includes("d.delivery_id = ? AND d.order_id = ? AND d.state = 'DELIVERED' AND o.state = 'COMPLETED')"), "ledger transition must independently prove the exact delivery is DELIVERED and its order COMPLETED");


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

assert.match(worker, /PAYPAL_CLIENT_ID/);
assert.match(worker, /PAYPAL_CLIENT_SECRET/);
assert.match(worker, /\/api\/payments\/paypal\/create/);
assert.match(worker, /\/api\/payments\/paypal\/capture/);
assert.match(worker, /\/api\/payments\/paypal\/webhook/);
assert.match(worker, /verify-webhook-signature/);
assert.match(worker, /PAYPAL_WEBHOOK_ID_NOT_CONFIGURED/);
assert.match(worker, /"PayPal-Request-Id": createRequestId/, "PayPal order creation must use a stable idempotency key");
assert.match(worker, /"PayPal-Request-Id": captureRequestId/, "PayPal capture retries must use a stable idempotency key");
assert.match(worker, /PAYPAL_CAPTURE_NOT_COMPLETED/, "webhook must reject capture events whose resource status is not COMPLETED");
assert.match(worker, /Number\(order\.amount\) !== amount/, "verified capture must match the current order amount");
assert.ok(worker.includes("provider IN ('paytabs','paypal')"), "delivery revenue gate must recognize verified PayPal payments");

const paypalCaptureStart = worker.indexOf("async function capturePayPalPayment");
const paypalWebhookStart = worker.indexOf("async function handlePayPalWebhook", paypalCaptureStart);
const paypalCapture = worker.slice(paypalCaptureStart, paypalWebhookStart);
assert.ok(paypalCaptureStart >= 0 && paypalWebhookStart > paypalCaptureStart, "PayPal capture handler must exist");
assert.ok(paypalCapture.indexOf("PAYMENT_AMOUNT_OR_CURRENCY_MISMATCH") < paypalCapture.indexOf('if (payment.state === "PAYMENT_VERIFIED")'), "PayPal capture must validate persisted order/payment amount and currency before idempotent success");
assert.match(paypalCapture, /state: "PAYMENT_VERIFIED_PENDING_DELIVERY"/, "idempotent capture response must not imply delivery or realized revenue");

// Regression guards: verified PayPal payment retries must repair dependent records.
const paypalVerifierStart = worker.indexOf("async function markPayPalPaymentVerified");
const paypalVerifierEnd = worker.indexOf("async function handlePayTabsReturn", paypalVerifierStart);
const paypalVerifier = worker.slice(paypalVerifierStart, paypalVerifierEnd);
assert.ok(paypalVerifierStart >= 0 && paypalVerifierEnd > paypalVerifierStart, "PayPal payment verifier must exist");
assert.ok(paypalVerifier.includes('new TextEncoder().encode("paypal-order:" + orderId)'), "stable recovery key missing");
assert.ok(paypalVerifier.includes("await env.BRAIN_DB.batch(["), "atomic D1 batch missing");
assert.match(paypalVerifier, /INSERT OR IGNORE INTO revenue_ledger/);
assert.match(paypalVerifier, /INSERT OR IGNORE INTO service_jobs/);
assert.match(paypalVerifier, /PAYPAL_REVENUE_LEDGER_RECONCILIATION_FAILED/);
assert.match(paypalVerifier, /PAYPAL_SERVICE_JOB_NOT_PERSISTED/);
assert.match(paypalVerifier, /PAYMENT_VERIFIED_PENDING_DELIVERY/);
console.log("PAYPAL_PARTIAL_FAILURE_RECOVERY_GATES=PASS");
console.log("PAYPAL_SANDBOX_STATIC_GATES=PASS");



assert.match(worker, /payload\.payment_result \|\| payload/, "PayTabs callback must support top-level response_status");
assert.match(worker, /transactionType !== "sale"/, "authorization/refund callbacks must not verify a sale payment");
const payTabsCallbackStart = worker.indexOf("async function handlePayTabsCallback");
const payTabsReturnStart = worker.indexOf("async function handlePayTabsReturn");
const payTabsCallback = worker.slice(payTabsCallbackStart, worker.indexOf("async function ", payTabsCallbackStart + 10));
assert.ok(payTabsCallbackStart >= 0 && payTabsReturnStart >= 0, "PayTabs callback/return handlers must exist");
assert.ok(payTabsCallback.indexOf("PAYMENT_AMOUNT_OR_CURRENCY_MISMATCH") < payTabsCallback.indexOf('if (payment.state === "PAYMENT_VERIFIED")'), "PayTabs callback must validate amount/currency before idempotent success");
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
assert.match(worker, /Number\(result\?\.meta\?\.changes\) !== 1/, "settlement must fail closed unless the conditional update changes exactly one row");
assert.match(worker, /SETTLEMENT_STATE_CONFLICT/, "a concurrent ledger state change must not be reported as realized revenue");
assert.match(settlementMigration, /CREATE UNIQUE INDEX IF NOT EXISTS idx_revenue_settlement_reference_unique/, "settlement reference must be unique");
assert.match(worker, /settlementDate/);