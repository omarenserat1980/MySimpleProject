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

## Delivery artifact trust boundary

- Set the Worker variable `BRAIN_DELIVERY_ALLOWED_ORIGINS` to a comma-separated allowlist of exact HTTPS origins that actually host trusted service artifacts (origins only; no paths).
- Keep this variable unset until the artifact host is selected and reviewed. In that state, `/health` reports `delivery_artifact_policy: NOT_CONFIGURED` and job completion fails closed.
- Job completion requires structured evidence, an HTTPS artifact URL on an allowlisted origin, and a 64-character SHA-256 digest. The digest is currently recorded as executor-supplied evidence; this Worker does not download the artifact or independently recompute the digest. Do not treat the digest alone as proof that the artifact contents are authentic.
- Before enabling production delivery, add an authenticated artifact verifier or signed-manifest verification and test it against the actual artifact provider. Do not use a broad wildcard origin or a user-controlled public upload host.

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

## Test vs Live revenue boundary

- `PAYTABS_MODE` defaults to `test`; Sandbox callbacks are recorded as `SANDBOX_PAYMENT_VERIFIED_PENDING_DELIVERY` and can never transition to `REVENUE_REALIZED`.
- The Cloudflare deploy workflow passes `PAYTABS_MODE` from the GitHub Actions variable `PAYTABS_MODE`; when that variable is absent it explicitly deploys `test`. The workflow accepts only `test` or `live`.
- Keep `PAYTABS_MODE` unset (safe default `test`) while validating sandbox. Set the GitHub Actions repository/environment variable `PAYTABS_MODE=live` only after PayTabs has approved and enabled the merchant for live payments and the Live Server Key/Profile ID are stored as production Worker secrets/variables. Never put credentials in source control or logs. Changing this variable does not itself prove that a live transaction or settlement occurred.
- A Live payment starts at `PAYMENT_VERIFIED_PENDING_DELIVERY`. Delivery confirmation advances it only to `DELIVERY_CONFIRMED_PENDING_SETTLEMENT`; delivery alone must never mark collected revenue.
- `REVENUE_REALIZED` and collected cash require a separate authenticated settlement/payout reconciliation that binds the provider settlement reference, transaction, amount, currency, and order. This Worker currently does not implement that independent settlement verifier, so it intentionally leaves revenue pending settlement and returns `revenue_realized=false`.
- Existing rows receive `environment='test'` via migration 0008; they are not retroactively promoted to Live.
