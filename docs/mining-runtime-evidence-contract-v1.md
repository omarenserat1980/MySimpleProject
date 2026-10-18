# Mining runtime evidence contract (v1)

This contract describes **sanitized, read-only observations** supplied by an explicitly authorized host diagnostic collector. It is not itself a collector or an attestation.

## Required envelope

```json
{
  "schema_version": 1,
  "evidence_id": "opaque-unique-id",
  "source": {
    "kind": "authorized_host_collector",
    "collector_version": "x.y.z",
    "host_id": "non-secret-stable-id"
  },
  "observed_at": "2026-01-01T00:00:00Z",
  "collection": {
    "mode": "read_only",
    "network_probes_performed": false,
    "credentials_read": false,
    "settings_changed": false,
    "miner_started_or_stopped": false
  },
  "observations": {
    "process_inventory": "UNKNOWN",
    "dns": "UNKNOWN",
    "tcp": "UNKNOWN",
    "tls": "UNKNOWN",
    "stratum": "UNKNOWN",
    "authorization": "UNKNOWN",
    "accepted_shares": "UNKNOWN",
    "account_match": "UNKNOWN"
  },
  "integrity": {
    "payload_sha256": "hex-sha256-of-canonical-payload",
    "signature": null,
    "signing_key_id": null
  }
}
```

## Allowed values

- `process_inventory`: `FOUND | NONE_FOUND | UNAVAILABLE | UNKNOWN`
- `dns`, `tcp`, `tls`, `stratum`: `PASS | FAIL | NOT_RUN | UNKNOWN`
- `authorization`: `ACCEPTED | REJECTED | NOT_TESTED | UNKNOWN`
- `accepted_shares`: `ACCEPTED_REPORTED | NONE_REPORTED | NOT_CHECKED | UNKNOWN`
- `account_match`: `MATCH | MISMATCH | NOT_CHECKED | UNKNOWN`

## Validation rules

1. Reject unknown schema versions, malformed timestamps, missing required envelope fields, invalid enum values, and oversized payloads.
2. Treat missing fields as `UNKNOWN`; never infer success from absence.
3. Record provenance, collection time, collector version, and integrity data. A hash detects accidental changes only; it does **not** authenticate the collector. A signature is meaningful only when verified against a trusted, independently provisioned public key.
4. Do not include passwords, access tokens, authorization payloads, full pool URLs containing secrets, raw protocol messages, or other credentials.
5. Observations from a caller-provided JSON file are untrusted until their source and integrity are independently validated.
6. A pool-side accepted-share report must be independently retrieved from an authorized pool telemetry source and correlated with worker identity and time window.
7. Neither accepted shares nor a valid envelope alone prove Brain generated the work, establish hashrate, or prove payout/revenue. Keep `real_mining_verified`, `brain_work_attribution_verified`, and `revenue_verified` false until their separate evidence gates pass.
8. Collection is read-only by default. No pool configuration changes, credential rotation, mining start/stop, or live Stratum submission are part of this contract.

## Status

This is a proposed interface contract for implementation and review. It does not claim that a host collector, signature verification, pool API integration, or real mining has already been implemented.
