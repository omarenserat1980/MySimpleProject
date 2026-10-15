# Bitcoin Live Mining Readiness — Phase 1

Status: **SCHEMA VALIDATOR ONLY — NOT LIVE MINING**

This phase adds a fail-closed validator for evidence collected by a separately operated, explicitly authorized worker. It does not install or execute a miner, contact a pool, create a wallet, or spend money.

## Added contract
- Bitcoin SHA-256d algorithm label, worker and pool identifiers.
- Timestamp freshness and observation window checks.
- Finite, non-negative hashrate and share counters.
- Canonical SHA-256 digest check to detect accidental or post-capture payload changes.
- Explicitly keeps `execution_authorized=false` and `revenue_verified=false`.

## Security boundary
A digest contained inside the same payload is **not authentication**: anyone who edits the payload can recompute it. A trusted collector or independently obtained signature/digest is still required. A reported `CONNECTED` value or accepted-share count is not independently verified by this validator.

## Requirements before a real acceptance run
1. Identify a user-owned worker with explicit authorization; no GitHub-hosted runner mining.
2. Configure a real Bitcoin SHA-256d Stratum pool endpoint and credentials locally through environment variables/secret storage only. Never commit credentials.
3. Capture protocol-derived session events and share counters from the worker/pool.
4. Verify source identity and evidence independently; keep pool connection, accepted shares, payout, and wallet-received BTC as separate gates.
5. Run tests, then a short authorized live test only if a real worker and pool account exist. Under the current zero-JOD constraint, do not buy hardware or rent cloud capacity.

The current known environment has no verified worker, pool session, wallet access, accepted share, or payout evidence. Therefore live mining and income remain **NOT PROVEN**.
