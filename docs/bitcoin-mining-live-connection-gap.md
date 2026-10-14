# Bitcoin Live Mining Connection Gap

Status: discovery finding; no live mining is running.

## Verified from the current main branch

- `brain_v12/brain/bitcoin_mining_intelligence_api.py` exposes status, analysis, and planning endpoints. Its status explicitly sets `real_mining_enabled=false`; its plan endpoint uses `DRY_RUN`, marks mining execution `DISABLED`, and returns `real_mining_started=false`.
- `brain_v12/brain/mining_engine.py` is an input-based economics calculator. Its profit gate remains `BLOCKED_REVENUE_UNVERIFIED`.
- `brain_v12/brain/mining_controller.py` defines a disabled-by-default policy and forbids mining in GitHub Actions. Its current miner registry targets RandomX/KawPow/CryptoNight/GhostRider rather than Bitcoin SHA-256 Stratum execution.
- `brain_v12/brain/asic_resource_adapter.py` explicitly does not connect to providers or start mining. External telemetry is not sufficient by itself to attest a real worker.
- `brain_v12/brain/worker_registry.py` is documented and implemented as software-only; physical-device and Termux workers are disabled.
- Existing tests cover dry-run behavior, simulator separation, and unverified revenue. A test result is not evidence of a live pool session.

## Required implementation sequence

1. Preserve the existing profit, spending, and release gates. Do not enable execution merely because a JSON record says `connected=true`.
2. Add a live-worker integration only for an explicitly authorized, user-owned host, outside GitHub Actions. For Bitcoin it must support SHA-256d and a documented Stratum protocol; the existing RandomX plan must not be relabeled as Bitcoin mining.
3. Capture protocol-derived connection and authorization outcomes, fresh measured hashrate, and accepted/rejected/stale share counters from the worker and/or pool. Identify the source and observation window.
4. Validate schema, timestamps, worker identity, finite nonnegative measurements, freshness, and artifact digest. Keep raw secrets out of evidence and logs.
5. Keep pool activity, payout, and received BTC as separate gates. Received BTC requires independent transaction and wallet-side confirmation.
6. Test fail-closed behavior with synthetic fixtures, clearly labeled as fixtures. Then run a separately authorized live acceptance test on a real worker. CI alone cannot pass the live gate.

## Current blocker

The repository does not currently prove a configured Bitcoin SHA-256 Stratum worker, and its worker registry disables physical/Termux workers. No pool endpoint, credentials, live worker telemetry, accepted share, or payout evidence was supplied by the inspected repository state. Consequently, a live mining claim must remain BLOCKED. No paid cloud resources should be provisioned under the zero-budget policy.
