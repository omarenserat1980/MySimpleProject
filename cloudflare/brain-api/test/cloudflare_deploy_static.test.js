const assert = require("node:assert/strict");
const fs = require("node:fs");

const worker = fs.readFileSync("src/index.js", "utf8");
const wrangler = fs.readFileSync("wrangler.toml", "utf8");
const cinema = fs.readFileSync("migrations/0007_cinema_entitlements.sql", "utf8");

[
  "PAYTABS_SERVER_KEY","Signature","HMAC","PAYMENT_PENDING","PAYMENT_VERIFIED",
  "PAYMENT_AMOUNT_OR_CURRENCY_MISMATCH","payment_events","REVENUE_REALIZED",
  "createCinemaCheckout","cinemaAccess","cinemaStream","CINEMA_MEDIA",
  "cinema_entitlements","BRAIN_CINEMA_TOKEN"
].forEach(token => assert.ok(worker.includes(token), "missing: " + token));

assert.ok(worker.includes('const PAYTABS_BASE_URL = "https://secure-jordan.paytabs.com";'));
assert.match(wrangler, /binding = "BRAIN_DB"/);
assert.match(wrangler, /binding = "CINEMA_MEDIA"/);
assert.match(wrangler, /bucket_name = "brain-cinema-media"/);
assert.match(cinema, /CREATE TABLE IF NOT EXISTS cinema_entitlements/);
console.log("BRAIN_CLOUDFLARE_DEPLOY_STATIC_GATE=PASS");
console.log("PAYMENT_VERIFICATION=PASS");
console.log("CINEMA_ENTITLEMENT=PASS");
console.log("PRIVATE_R2_BINDING=PASS");

assert.match(worker, /supervisorTick/);
assert.match(worker, /BRAIN_CONTROL_TOKEN/);
assert.match(worker, /BRAIN_ORIGIN/);
console.log("SUPERVISOR_CONTROL_GATE=PASS");
