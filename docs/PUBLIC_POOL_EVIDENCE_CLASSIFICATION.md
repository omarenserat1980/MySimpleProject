# Public Pool Evidence Classification

## Purpose

Electronic Brain classifies local Stratum logs separately from pool-side aggregate telemetry. The classifier is offline and deterministic: it does not start a miner, make network requests, change pool settings, submit shares, or create accounting entries.

## Evidence levels

- `STRATUM_CONNECTION_OBSERVED`: a local log contains a Stratum session identifier.
- `STRATUM_CONNECTED_WORK_OBSERVED_SHARES_UNVERIFIED`: local logs show a session and work/job, but no accepted share is evidenced.
- `POOL_SHARE_ACTIVITY_OBSERVED_NOT_REVENUE_PROOF`: an accepted marker exists in the supplied miner log or an independently collected pool snapshot reports positive address-level counters. This does not attribute a specific share to Brain.
- `NO_LOCAL_MINER_SESSION_EVIDENCE`: no local session evidence is available.

The classifier always leaves `payout_verified`, `revenue_verified`, and `brain_runtime_activity_verified` false. Pool address telemetry is not proof of which process submitted a share, and share acceptance is not proof of a realized payout.

## Run focused tests

```bash
python -m pytest -q brain_v12/tests/test_public_pool_local_evidence.py
```

## Current observed run

The latest Public Pool address snapshot returned zero workers, zero accepted shares, zero credited difficulty, and no expected payout. The local miner log shows a Stratum session and jobs, but no accepted/rejected marker in the saved log. Therefore current status is `STRATUM_CONNECTED_WORK_OBSERVED_SHARES_UNVERIFIED`; income remains unverified.

Evidence files are generated locally under `~/.brain/evidence/` and are not automatically committed or uploaded.
