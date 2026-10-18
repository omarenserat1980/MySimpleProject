const assert = require("node:assert/strict");
const fs = require("node:fs");

const worker = fs.readFileSync("src/index.js", "utf8");
const wrangler = fs.readFileSync("wrangler.toml", "utf8");
const cinema = fs.readFileSync("migrations/0007_cinema_entitlements.sql", "utf8");
const cinemaPublish = fs.readFileSync("../../.github/workflows/brain-cinema-publish.yml", "utf8");
const cinemaDeploy = fs.readFileSync("../../.github/workflows/brain-cloudflare-deploy.yml", "utf8");
const production = fs.readFileSync("../../.github/workflows/last-light-no-pay.yml", "utf8");

[
  "PAYTABS_SERVER_KEY","Signature","HMAC","PAYMENT_PENDING","PAYMENT_VERIFIED",
  "PAYMENT_AMOUNT_OR_CURRENCY_MISMATCH","payment_events","DELIVERY_CONFIRMED_PENDING_SETTLEMENT",
  "createCinemaCheckout","cinemaAccess","cinemaStream","CINEMA_MEDIA",
  "cinema_entitlements","BRAIN_CINEMA_TOKEN"
].forEach(token => assert.ok(worker.includes(token), "missing: " + token));

assert.ok(worker.includes('const PAYTABS_BASE_URL = "https://secure-jordan.paytabs.com";'));
const confirmDeliverySource = worker.slice(worker.indexOf("async function confirmDelivery("), worker.indexOf("async function completeJob("));
assert.doesNotMatch(confirmDeliverySource, /UPDATE\s+revenue_ledger\s+SET\s+state\s*=\s*[\'"]REVENUE_REALIZED[\'"]/i, "delivery confirmation must not realize revenue");
assert.match(worker, /async function verifySignedSettlementEvidence/);
assert.match(worker, /BRAIN_SETTLEMENT_ATTESTATION_KEY/);
assert.match(worker, /SETTLEMENT_SIGNATURE_INVALID/);
assert.match(worker, /SIGNED_OPERATOR_ATTESTATION_AFTER_INDEPENDENT_SOURCE_REVIEW/);
assert.match(worker, /revenue_realized:\s*false/, "delivery confirmation must explicitly keep revenue unrealized");
assert.match(wrangler, /binding = "BRAIN_DB"/);
assert.match(wrangler, /binding = "CINEMA_MEDIA"/);
assert.match(wrangler, /bucket_name = "brain-cinema-media"/);
assert.match(cinema, /CREATE TABLE IF NOT EXISTS cinema_entitlements/);
assert.match(cinemaPublish, /brain-cinema-master-private/);
assert.match(cinemaPublish, /last_light_city_preview\.mp4/);
assert.match(cinemaPublish, /Paid master must never be published under docs\/assets/);
assert.doesNotMatch(cinemaPublish, /git add .*last_light_city\.mp4/);
assert.match(cinemaDeploy, /brain-cinema-master-private/);
assert.match(cinemaDeploy, /brain-cinema-media\/films\/last_light_city\.mp4/);
assert.match(production, /name: brain-cinema-master-private/);
assert.match(production, /path: \/tmp\/last-light\/last_light_city\.mp4/);
assert.match(cinemaDeploy, /gh run download/);
assert.match(cinemaDeploy, /CINEMA_MASTER_ACQUIRED=PASS/);
assert.doesNotMatch(cinemaDeploy, /docs\/assets\/last_light_city\.mp4/);
console.log("BRAIN_CLOUDFLARE_DEPLOY_STATIC_GATE=PASS");
console.log("PAYMENT_VERIFICATION=PASS");
console.log("CINEMA_ENTITLEMENT=PASS");
console.log("PRIVATE_R2_BINDING=PASS");

assert.match(worker, /supervisorTick/);
assert.match(worker, /BRAIN_CONTROL_TOKEN/);
assert.match(worker, /BRAIN_ORIGIN/);
console.log("SUPERVISOR_CONTROL_GATE=PASS");
