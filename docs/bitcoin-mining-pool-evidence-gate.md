# Bitcoin Mining Pool Evidence Gate

Status: specification only. This document does not claim that a worker is running, a pool is connected, shares have been accepted, or revenue has been received.

## Required evidence

The live-mining gate must fail closed unless all of these conditions are satisfied by evidence collected from an authorized worker:

1. **Pool connection** — successful Stratum session to a configured pool, with pool host/port, protocol, worker identifier, connection timestamp, and a successful subscribe/authorize result. Never store passwords, tokens, or wallet secrets in evidence.
2. **Real hashrate** — a numeric measurement with unit, measurement window, timestamp, and source (worker or pool-side API). Do not substitute a configured target, estimate, synthetic value, or test fixture.
3. **Accepted shares** — cumulative and interval accepted-share counts from the worker or pool, plus rejected/stale counts where available. Require at least one accepted share for the accepted-share gate. A local log line alone is weaker than pool-side evidence and must be labeled accordingly.
4. **Integrity and freshness** — UTC timestamps, worker identity, evidence source, schema version, and SHA-256 digest for the finalized evidence artifact. Reject malformed, stale, contradictory, or fixture-marked records.
5. **Independent revenue gate** — pool connection, hashrate, and accepted shares prove mining activity only. They do not prove a payout. Payout and received BTC require separate payout records, transaction ID, and wallet-side confirmation.

## Evidence artifact schema

Store one JSON record per observation, with fields equivalent to:

```json
{
  "schema_version": "1.0",
  "observed_at_utc": "RFC3339 UTC timestamp",
  "mode": "live",
  "worker_id": "authorized-worker-id",
  "pool": {
    "host": "configured-pool-host",
    "port": 3333,
    "protocol": "stratum",
    "connected": true,
    "authorized": true,
    "connected_at_utc": "RFC3339 UTC timestamp",
    "source": "worker-or-pool-api"
  },
  "hashrate": {
    "value": 0,
    "unit": "H/s",
    "window_seconds": 60,
    "source": "worker-or-pool-api"
  },
  "shares": {
    "accepted_total": 0,
    "accepted_interval": 0,
    "rejected_total": 0,
    "stale_total": 0,
    "source": "worker-or-pool-api"
  },
  "evidence_artifact_sha256": "hex-digest",
  "fixture": false
}
```

The example values are placeholders, not mining measurements. Producers must replace them with observations and validators must reject placeholder or fixture data.

## Gate decisions

- `POOL_CONNECTED`: connection and authorization both confirmed by fresh live evidence.
- `HASHRATE_OBSERVED`: measured hashrate is numeric, positive, fresh, and source-attributed.
- `SHARE_ACCEPTED`: at least one accepted share is reported by a live source.
- `MINING_ACTIVITY_VERIFIED`: all three preceding gates pass and the artifact integrity check passes.
- `PAYOUT_VERIFIED`: a separate payout record is reconciled with a transaction ID and independently checked wallet/blockchain confirmation.
- `REVENUE_REALIZED`: BTC receipt is independently verified; do not infer it from shares, estimated earnings, or pool dashboards alone.

## Safety and execution constraints

- Never run mining workloads in GitHub Actions CI or other ephemeral CI runners.
- Execute only on explicitly authorized compute, within its resource and electricity limits.
- Keep pool credentials and wallet keys in a secret manager or protected local environment; never commit them or include them in evidence.
- CI may validate schemas, fixtures, and fail-closed behavior. CI results must never be represented as proof of live mining.
- Do not claim success until real evidence artifacts exist and their hashes and timestamps can be inspected.
