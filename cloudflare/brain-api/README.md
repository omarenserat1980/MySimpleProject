# BRAIN Cloud Commercial Edge

This Worker is the provider-neutral public HTTPS edge for BRAIN commercial payments.
It does not depend on Render or Oracle.

## Architecture

Browser / BRAIN Marketing -> Cloudflare Worker -> PayTabs Jordan Hosted Payment Page -> PayTabs Callback -> HMAC-SHA256 verification -> Cloudflare D1 evidence -> PAYMENT_VERIFIED -> BRAIN commercial ledger.

The Worker can also proxy other BRAIN API routes to an optional BRAIN_ORIGIN. Payment verification does not depend on that origin.

## Required runtime configuration

Cloudflare Worker secret: PAYTABS_SERVER_KEY
Cloudflare Worker variable: PAYTABS_PROFILE_ID
D1 binding: BRAIN_DB (database name: brain-commercial)

The GitHub deployment workflow provisions/binds the D1 database and applies migrations when Cloudflare credentials are configured. D1 migrations are versioned under migrations/.

## Payment safety

- Uses the Jordan endpoint https://secure-jordan.paytabs.com/payment/request.
- Never exposes the PayTabs Server Key to the browser.
- Prices paid plans server-side.
- Stores expected order amount/currency before checkout.
- Verifies PayTabs Signature using HMAC-SHA256 over the complete callback body.
- Verifies order ID, amount, currency, transaction reference and payment_result.response_status == A.
- Records an idempotent payment event in D1.
- Only then changes the order/payment state to PAYMENT_VERIFIED.
- Treats the Return URL as UX, not payment evidence.

## Deployment gate

The code is ready for deployment, but the commercial system is not declared live until a real deployed Worker returns /health, a real Sandbox checkout is completed, PayTabs reaches the Callback, and D1 contains the resulting evidence.

PAYMENT_VERIFIED is evidence-gated.
REVENUE_REALIZED remains false until payment evidence is independently confirmed.