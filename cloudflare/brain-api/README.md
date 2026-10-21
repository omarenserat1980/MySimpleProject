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
- Job completion requires structured evidence, an HTTPS artifact URL on an allowlisted origin, and a 64-character SHA-256 digest. Before mutating job/order/delivery state, the Worker fetches the artifact without following redirects, streams and caps the body at 10 MiB, and independently recomputes SHA-256; fetch errors, missing bodies, oversized artifacts, redirects, and digest mismatches fail closed.
- The allowlisted artifact origin must serve the exact bytes without a redirect. Private artifact providers that require authentication need a dedicated authenticated verifier or signed-manifest design; do not weaken the allowlist or accept executor-supplied hashes without verification. Validate the byte limit against the actual product artifact sizes before production delivery.

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
- `REVENUE_REALIZED` is gated by the authenticated `POST /api/revenue/settlement/verify` signed-operator-attestation flow documented below. This endpoint does not independently fetch or validate the provider/bank report; an authorized operator must review the original source evidence outside the Worker before signing. The endpoint then validates the signature, live ledger state, transaction reference, gross amount, currency, and unique settlement reference, and only reports realization if the conditional database update changes exactly one row. A successful API response is not a substitute for independently retained provider/bank evidence, and no revenue should be claimed without that evidence.
- Existing rows receive `environment='test'` via migration 0008; they are not retroactively promoted to Live.


## Read-only transaction reconciliation (not settlement)

The authenticated `POST /api/payments/paytabs/reconcile-query` endpoint queries PayTabs' documented `/payment/query` endpoint for a live revenue row that is already `DELIVERY_CONFIRMED_PENDING_SETTLEMENT`. It checks the provider transaction reference, cart/order ID, amount, currency, approved response status, and Sale transaction type before recording a timestamped audit observation in the revenue evidence.

This endpoint is read-only against PayTabs and is **not** proof of payout or merchant-bank settlement. A successful result explicitly returns `settlement_verified: false` and `revenue_realized: false`; the ledger state remains pending settlement. It must not be used to bypass an independently verified settlement/payout report or bank reconciliation. It requires `BRAIN_CONTROL_TOKEN`, `PAYTABS_SERVER_KEY`, and `PAYTABS_PROFILE_ID`; no secrets belong in source control.


## Signed settlement evidence gate

`POST /api/revenue/settlement/verify` is an authenticated, fail-closed gate for recording revenue as realized only after an authorized operator independently reviews a PayTabs settlement report or bank statement. It requires both `BRAIN_CONTROL_TOKEN` and a separately provisioned `BRAIN_SETTLEMENT_ATTESTATION_KEY` (at least 32 characters). Never commit either secret.

The signed JSON fields are canonicalized in this exact order: `tran_ref`, `settlement_reference`, `settled_amount`, `currency`, `settlement_date`, `source`, `report_sha256`. The `signature` field is the lowercase hex HMAC-SHA256 of the compact JSON serialization of those fields, using the separately provisioned attestation key. `source` must be `PAYTABS_SETTLEMENT_REPORT` or `BANK_STATEMENT`; `report_sha256` is the SHA-256 digest of the source evidence file reviewed by the operator.

This endpoint does not fetch or independently validate the source report itself. The signed attestation is an operator assertion that the source evidence was reviewed independently; it must only be generated after checking the provider/bank record outside this endpoint. The endpoint checks the transaction reference, live environment, pending-settlement state, gross amount, currency, signature, and conditional state transition. If the evidence has not been independently reviewed, do not sign or submit it. A successful transaction query alone is never sufficient to realize revenue.


Settlement references are persisted in a dedicated nullable column with a unique partial index (migration `0009_settlement_reference.sql`). A single provider settlement reference cannot be assigned to multiple revenue rows; the update also requires the ledger row's settlement reference to remain empty. Keep source-report review and attestation generation outside the Worker, and never reuse a settlement reference.
