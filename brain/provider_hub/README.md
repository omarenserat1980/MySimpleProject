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
