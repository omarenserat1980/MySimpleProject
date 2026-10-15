# Brain Local Stratum Bridge

Status: implementation scaffold; no live connection has been performed by this change.

## Purpose
Provide an explicit local-only Stratum subscribe/authorize probe for a user-owned worker. It is not a miner: it performs no proof-of-work, submits no shares, and cannot establish payout or revenue.

## Enable only on the authorized host
Set these environment variables locally; do not put values in GitHub files, CI variables, logs, or chat:
- `BRAIN_ENABLE_LIVE_STRATUM_BRIDGE=1`
- `BRAIN_MINING_WORKER_OWNED=1`
- `BRAIN_MINING_AUTHORIZED=1`
- `BRAIN_STRATUM_HOST`, `BRAIN_STRATUM_PORT`
- `BRAIN_STRATUM_USERNAME`, `BRAIN_STRATUM_PASSWORD`
- `BRAIN_STRATUM_TLS=1` (mandatory; the bridge refuses plaintext Stratum)

The bridge refuses CI/GitHub Actions. Use a pool account and endpoint only if you are authorized to do so. Keep secrets in local environment or a secret manager. TLS is mandatory to protect credentials in transit. Connection and authorization may expose account/worker identifiers to the pool.

## Current invocation and tests
The bridge currently exposes `probe_stratum_connection()` as a Python function; this change does not add a command-line entry point or a Brain HTTP endpoint. Do not assume the bridge has run just because the module exists. The isolated regression tests can be run from the repository root with:

```sh
python -m pytest -q brain_v12/tests/test_bitcoin_stratum_bridge.py brain_v12/tests/test_bitcoin_stratum_evidence.py
```

Do not run a live probe until you have a user-owned/authorized worker and a pool's verified TLS endpoint. Never use production credentials in tests or CI.

## Important limits
A successful result means only that Stratum subscribe and authorization succeeded. It does not prove SHA-256d hashing, accepted shares, BTC payout, or profitability. The response deliberately reports zero shares and `execution_authorized=false`. A real mining worker/ASIC or a separately installed and authorized miner is still required.
