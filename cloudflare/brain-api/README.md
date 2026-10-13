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

## PayPal Sandbox adapter (PR #591)

The Worker now exposes:

- `POST /api/payments/paypal/create`: requires an authenticated BRAIN client, an existing D1 order owned by that client, and server-side order amount/currency. It creates a PayPal Sandbox order and stores the provider order ID in D1 before returning the approval URL.
- `POST /api/payments/paypal/capture`: requires the authenticated owner of the stored PayPal order and requests capture through PayPal Sandbox. Its response is informational only; the verified PayPal webhook remains the sole authority for changing payment state or creating pending-delivery ledger evidence.
- `POST /api/payments/paypal/webhook`: verifies the PayPal transmission headers and event with PayPal's Sandbox verification endpoint, then fetches the provider order and reconciles its completed status, `reference_id`, `invoice_id`, capture ID, amount, and currency against the stored D1 payment before recording payment evidence. Repeated verified captures do not create a second payment ledger entry.

Required Worker secrets:

- `PAYPAL_CLIENT_ID`
- `PAYPAL_CLIENT_SECRET`
- `PAYPAL_WEBHOOK_ID` — the ID of the webhook configured in the PayPal Developer Dashboard.

The integration is Sandbox-only and does not claim a live transaction. A verified capture enters `PAYMENT_VERIFIED_PENDING_DELIVERY`; the existing delivery gate must confirm delivery before `REVENUE_REALIZED`. Unit/static CI tests do not prove the Worker is deployed or that PayPal delivered a real Sandbox webhook. Keep PR #591 open until a deployed Sandbox E2E run and D1 evidence have been reviewed.
