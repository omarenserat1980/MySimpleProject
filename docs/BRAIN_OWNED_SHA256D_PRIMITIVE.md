# Brain-Owned SHA-256d Proof-of-Work Primitive

## Scope

This change adds a bounded, deterministic Bitcoin SHA-256d proof-of-work primitive and explicit 80-byte header helpers. It is a software library, not a pool miner. It does not implement Stratum session management, coinbase construction, merkle-path generation, share submission, wallet operations, payout reconciliation, or automatic work scheduling.

## Compute placement and safety

- Android/Termux is a connectivity/observation gateway and is rejected as a compute host by `execution_host_gate`.
- GitHub Actions/CI must never be used for live mining.
- The nonce search is not started automatically and is bounded to at most 10,000,000 hashes per call (default 1,000,000).
- The gate always returns `execution_allowed: false`; a positive gate result is only a review state, never an authorization to start mining.
- The kernel's successful result is `NONCE_FOUND_UNSUBMITTED`. It proves only that a candidate header hash meets the supplied target; it does not prove pool acceptance or revenue.
- Live mining remains blocked until a separately reviewed Brain-owned Linux compute host, attestation, resource budget, compatible pool adapter, protected credentials, explicit authorization, accepted-share evidence, and payout reconciliation are independently verified.

## Verification

Tests cover bounded nonce search, SHA-256d, strict header sizes and fields, compact target decoding, and the Bitcoin genesis-block known hash. All generated/test evidence must retain its actual provenance; simulation and local unit tests are not real mining evidence.
