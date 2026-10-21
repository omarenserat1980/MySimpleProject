# Solo CKPool Read-only Integration

## Scope

`brain_v12/brain/ckpool_readonly_collector.py` retrieves public pool-wide CKPool telemetry from `https://raw.stats.ckpool.org/pool/pool.status`. It does not connect a miner, submit work, request account credentials, or enable financial execution.

Optional address-level telemetry can be requested with `--address <public-BTC-address>`. The address is validated before URL construction and is not copied into the generated report. Do not pass private keys, seed phrases, API tokens, or other secrets.

## Run

From the repository root in Termux:

```sh
PYTHONPATH=. python -m brain_v12.brain.ckpool_readonly_collector
```

Optional user statistics:

```sh
PYTHONPATH=. python -m brain_v12.brain.ckpool_readonly_collector --address '<PUBLIC_BTC_ADDRESS>'
```

The report is JSON on stdout. To retain a local evidence snapshot, redirect it to a user-owned path. Pool-wide hashrate and share counters describe CKPool as a whole; they do not establish that this phone or Brain submitted any shares.

## Verification

```sh
python -m pytest -q brain_v12/tests/test_ckpool_readonly_collector.py
```

The collector deliberately leaves `local_miner_started`, `local_hashrate_verified`, `local_share_acceptance_verified`, `block_found_verified`, `payout_verified`, and `revenue_realized` false. A payout requires separate independently verifiable block/transaction evidence. Solo mining has highly uncertain outcomes and is not a predictable income stream.
