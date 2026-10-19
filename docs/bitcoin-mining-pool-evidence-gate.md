# Bitcoin Mining Pool Evidence Gate

Status: schema/integrity validation only. This document and its validator do not claim that a worker is running, a pool is connected, shares have been accepted, or revenue has been received.

## Required evidence

The evidence validator checks the shape and internal consistency of a supplied artifact. It does **not** authenticate the source, establish that the record came from Braiins Pool, or prove that Brain generated the work. A SHA-256 digest over caller-supplied JSON only detects later changes relative to that digest; the caller can create both the JSON and its digest.

A future live-mining gate must fail closed unless all of these conditions are satisfied by evidence collected and authenticated by a trusted server-side verifier:

1. **Pool connection** — successful Stratum session to a configured pool, with pool host/port, protocol, worker identifier, connection timestamp, and successful subscribe/authorize result. Never store passwords, tokens, or wallet secrets in evidence.
2. **Real hashrate** — numeric measurement with unit, measurement window, timestamp, and source. Identify worker-reported data separately from pool-side API data.
3. **Accepted shares** — cumulative and interval accepted-share counts from the pool-side API or other independently authenticated source, plus rejected/stale counts where available. A caller-provided count or local log alone is not proof of pool acceptance.
4. **Integrity and freshness** — UTC timestamps, worker identity, schema version, evidence source, and SHA-256 digest for the finalized evidence artifact. Reject malformed, stale, contradictory, or fixture-marked records.
5. **Independent revenue gate** — pool connection, hashrate, and accepted shares do not prove payout. Payout and received BTC require separate payout records, transaction ID, and independently checked wallet-side confirmation.

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
    "source": "pool-api"
  },
  "evidence_artifact_sha256": "hex-digest",
  "fixture": false
}
```

Example values are placeholders, not mining measurements. A digest proves neither source authenticity nor a live pool event.

## Gate decisions

- `EVIDENCE_SCHEMA_VALIDATED_NOT_AUTHENTICATED`: structure, timestamp freshness, and digest checks passed. This is **not** a mining-activity verification.
- `BLOCKED`: one or more schema, freshness, source-field, or digest checks failed.
- `MINING_ACTIVITY_VERIFIED`: may only be asserted by a trusted server-side verifier after independently authenticating pool-side evidence and linking it to the Brain runtime. The schema validator in this module always returns `mining_activity_verified: false`.
- `PAYOUT_VERIFIED`: requires a separate payout record reconciled with a transaction ID and independently checked wallet/blockchain confirmation.
- `REVENUE_REALIZED`: requires independent verification of the actual receipt; never infer it from shares, estimates, or a dashboard alone.

## Safety and execution constraints

- Never run mining workloads in GitHub Actions CI or other ephemeral CI runners.
- Execute only on explicitly authorized compute, within resource and electricity limits.
- Keep pool credentials and wallet keys in a secret manager or protected local environment; never commit them or include them in evidence.
- CI may validate schemas, fixtures, and fail-closed behavior. CI results are not proof of live mining.
- Do not claim success until real evidence is collected from an authenticated source, linked to the Brain runtime, and its freshness and integrity can be inspected.
