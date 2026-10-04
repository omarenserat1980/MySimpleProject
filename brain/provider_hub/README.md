# BRAIN Provider Hub

Provider-neutral control layer for BRAIN commercial services.

## Rules
- Providers are adapters, never the source of truth.
- Core business states remain in BRAIN.
- A provider can be replaced without changing customer/order state machines.
- A provider becomes active only after health checks and evidence-producing integration tests.
- Secrets never live in the repository.
- Payment success requires verified provider evidence/webhook.
- Provider failure must preserve orders and enter a recoverable provider-unavailable state.

## Adapter classes
runtime, payment, email, database, storage, media.

## Lifecycle
DISCOVERED -> CONFIGURED -> HEALTHY -> VERIFIED -> ACTIVE
ACTIVE -> DEGRADED -> FAILOVER -> RECOVERING -> VERIFIED

## Commercial safety
Provider switching must never duplicate a payment, duplicate revenue, lose an order, bypass authorization, or claim delivery without evidence.

The companion UI in brain/provider_hub is an operator dashboard and registry. It contains no credentials.

## PayTabs Jordan configuration

The PayTabs adapter reads credentials only from runtime environment variables:

- `PAYTABS_PROFILE_ID` — non-secret profile identifier (currently configured as the Jordan test profile outside source control).
- `PAYTABS_SERVER_KEY` — secret; store only in the deployment secret manager / GitHub Actions secret store when CI needs it.
- `PAYTABS_BASE_URL` — optional; defaults to `https://secure-jordan.paytabs.com` and rejects non-Jordan PayTabs endpoints.

Never paste a Server Key into source files, logs, artifacts, issues, or chat. Rotate any key that has been exposed.

The adapter is fail-closed when the required environment variables are missing or the endpoint is not the approved Jordan endpoint. Unit tests use a fake transport and never contact PayTabs.
