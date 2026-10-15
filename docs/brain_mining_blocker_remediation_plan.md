# Brain Mining Blocker Remediation Plan

Status: implementation plan only; no live worker connection is claimed.

## Objective
Have Brain enumerate, assign, and remediate the blockers to connecting an explicitly owned Bitcoin SHA-256d worker, while keeping evidence and spending gates fail-closed.

## Blockers and actions

1. **Worker identity and reachability**
   - Identify the already-existing worker through a documented local API, authenticated agent, or owner-authorized SSH route.
   - Do not invent an endpoint or attempt to discover credentials.
   - Record worker ID, supported algorithm, operating environment, and permitted control actions.

2. **Authenticated Brain-to-worker channel**
   - Add an authenticated heartbeat/status API or client for the actual worker interface.
   - Require HTTPS/TLS, a strong token held only in the worker/Brain environment, constant-time token comparison, input validation, freshness checks, and redaction of secrets.
   - Do not store credentials in source control or log them.

3. **Worker registration and lease**
   - Register only the explicitly authorized worker.
   - Use bounded leases and expiring heartbeats; mark the worker offline when telemetry expires.
   - Do not enable arbitrary physical-device discovery or unrestricted remote command execution.

4. **Bitcoin SHA-256d execution evidence**
   - Confirm the worker is actually running an authorized SHA-256d miner.
   - Collect timestamped hashrate and accepted/rejected/stale share counters.
   - Label worker self-reports as unverified until reconciled with independent pool-side evidence.

5. **Pool-side acceptance**
   - Verify the configured pool endpoint and TLS status without exposing credentials.
   - Require pool-side accepted-share evidence before marking pool acceptance as verified.
   - Keep connection/authentication success separate from proof-of-work and accepted shares.

6. **Revenue gate**
   - Keep revenue unverified until a real pool payout is reconciled with an on-chain transaction and the owner's wallet receipt.
   - Never claim profit from benchmark output, simulation, worker self-report, or an accepted share alone.

7. **Safe remediation loop**
   - For each blocker: capture current evidence, make one bounded change, run focused local checks, inspect the diff, and record the result.
   - Do not use GitHub Actions as a live miner or start paid resources.
   - Do not auto-merge or enable live execution merely because a status field says connected.

## Completion criteria
- The real worker is identified and reachable through an owner-authorized interface.
- Brain authenticates the worker and receives fresh telemetry.
- Pool-side accepted shares are independently evidenced.
- Revenue remains a separate gate and is only marked verified with payout and wallet evidence.
- Every claim points to timestamped, sanitized evidence.

## Current confirmed limitation
Repository inspection shows the mining intelligence API is analysis/dry-run only, the worker registry is software-only, and the Stratum bridge is a connection/authorization probe rather than a miner. This plan does not itself connect or start a worker.
