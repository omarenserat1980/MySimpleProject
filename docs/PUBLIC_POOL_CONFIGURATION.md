# Public Pool configuration reference

This file mirrors the public connection settings supplied for Public Pool. It is a
configuration reference for Electronic Brain; it does **not** launch a miner, connect
to the pool, create a worker, or establish earnings.

## Modes and endpoints

| Mode | Stratum V1 | Stratum V1 + TLS |
| --- | --- | --- |
| Solo | `stratum+tcp://public-pool.io:3333` | `stratum+tls://public-pool.io:4333` |
| PPLNS | `stratum+tcp://public-pool.io:13333` | `stratum+tls://public-pool.io:14333` |

The supplied page also lists Stratum V2 on ports `23330` (Solo) and `23331`
(PPLNS), and DATUM on port `23336`. The current readiness module does not configure
or enable those protocols.

### Miner-client TLS scheme

The page uses `stratum+tls://`. The existing cpuminer build used in local diagnostics
expects `stratum+tcps://` for TLS. Both representations are documented in
`brain_v12/business/public_pool_readiness.py`; select the scheme supported by the
specific miner client rather than blindly copying it between clients.

## Worker identity

Public Pool expects the username format:

`<your Bitcoin receiving address>.<worker name>`

The preferred label requested for this device is `Realme01`. Historical local
references also include `brain-realme` and `realme-01`; confirm the existing worker
in the pool dashboard before renaming anything. A worker label alone is not proof
that a pool currently sees the worker.

The Termux launcher is `scripts/run-public-pool-pplns.sh`. It defaults to
`Realme01` and accepts an optional `BRAIN_MINING_WORKER_NAME` override, validated
against letters, digits, underscore, and hyphen. It prompts for the payout address
at launch rather than saving it in the repository. Launching this script starts
mining; do not run it during read-only diagnosis.

Set local configuration through environment variables (never commit the payout
address):

- `BRAIN_MINING_PAYOUT_ADDRESS` — user's own public receiving address
- `BRAIN_MINING_WORKER_NAME` — optional; defaults to `Realme01`
- `BRAIN_PUBLIC_POOL_MODE` — optional; `solo` or `pplns`; defaults to `pplns`

Do not store private keys, seed phrases, access tokens, or pool-specific keys in Git.
The DATUM key displayed by the website is intentionally not copied into this repo.

## Safety and evidence gates

The readiness module is local-only. It does not open network connections or start a
miner. Its status means only that the local settings have a valid shape and are ready
for manual review.

Keep these claims separate:

1. **Configured** — local settings are present and syntactically valid.
2. **Connected** — a miner log confirms a Stratum session.
3. **Hashing** — a local miner reports a hashrate.
4. **Accepted work** — pool-side telemetry or an explicit accepted-share response
   confirms accepted shares.
5. **Revenue** — a real payout is independently evidenced.

The recent local diagnostic observed a Stratum work restart and approximately
0.79 MH/s, but did not verify accepted shares or current worker visibility. No
payout or profitability is claimed. Tests must remain offline and must not start
mining.

## Safe offline tests

From the repository root:

```sh
python -m unittest brain_v12.business.test_public_pool_readiness -v
```
