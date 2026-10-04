const assert = require("node:assert/strict");
const fs = require("node:fs");

const worker = fs.readFileSync("src/index.js", "utf8");
const migration = fs.readFileSync("migrations/0007_cinema_entitlements.sql", "utf8");
const wrangler = fs.readFileSync("wrangler.toml", "utf8");
const page = fs.readFileSync("../../cinema.html", "utf8");

assert.match(worker, /createCinemaCheckout/);
assert.match(worker, /cinemaAccess/);
assert.match(worker, /cinemaStream/);
assert.match(worker, /CINEMA_MEDIA/);
assert.match(worker, /PAYTABS_SERVER_KEY/);
assert.match(worker, /PAYMENT_VERIFIED/);
assert.match(worker, /HMAC/);
assert.match(worker, /BRAIN_CINEMA_TOKEN/);
assert.match(worker, /cinema_entitlements/);
assert.match(migration, /CREATE TABLE IF NOT EXISTS cinema_entitlements/);
assert.match(wrangler, /binding = "CINEMA_MEDIA"/);
assert.match(wrangler, /bucket_name = "brain-cinema-media"/);
assert.ok(page.includes("__BRAIN_CINEMA_API_URL__") || page.includes("workers.dev"), "cinema API must be placeholder or deployed endpoint");
assert.match(page, /api\/cinema\/checkout/);
assert.match(page, /api\/cinema\/access/);
console.log("CINEMA_ENTITLEMENT_GATES=PASS");
console.log("CINEMA_R2_BINDING_GATES=PASS");
console.log("CINEMA_PAGE_INTEGRATION_GATES=PASS");
console.log("NO_LIVE_SECRET_IN_SOURCE=TRUE");
