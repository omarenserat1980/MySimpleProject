# Brain Software Capability Promotion Gate

The candidate catalog is observational only. This gate evaluates a supplied
`brain-capability-evidence/v1` JSON document against the catalog's
capability-specific requirements. It does not activate capabilities.

## Evidence contract

Each document contains:
- `schema`: `brain-capability-evidence/v1`
- `capability_id`: exact capability ID from the candidate catalog
- `checks`: one entry per catalog requirement, each with exact `requirement`,
  `result` equal to `PASS`, a non-empty `evidence_ref`, and timezone-aware
  ISO-8601 `observed_at` timestamp.

Evidence must be fresh (24 hours by default), not timestamped in the future,
and must satisfy every requirement. Missing, failed, stale, malformed, mismatched,
or unreferenced evidence blocks the decision.

## Example invocation

```powershell
python -m brain_v12.brain.software_capability_promotion_gate `
  --capability-id local_python_runtime `
  --evidence .\local-python-evidence.json `
  --output .\local-python-promotion-review.json
```

A successful exit code means only `ELIGIBLE_FOR_HUMAN_REVIEW`. It is not an
authorization to register an executor. A blocked decision exits with code 2.
The report always keeps `automatic_registration_allowed=false` and
`executor_state=NOT_REGISTERED`. No registry is imported or mutated, no
network probes are performed, and no generated code is executed.

For remote device execution, evidence must independently prove identity,
authentication/attestation, a fresh heartbeat, and a bounded task result.
For physical mining, pool worker telemetry, physical-device evidence, and
fresh hashrate evidence are mandatory. CI tests and local discovery do not
satisfy those live-evidence requirements.
