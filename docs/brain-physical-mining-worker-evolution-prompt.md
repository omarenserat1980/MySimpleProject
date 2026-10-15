# Brain Physical Mining Worker — Improvement Backlog and Master Prompt

## Objective

Connect Brain to an explicitly authorized physical SHA-256d worker through an authenticated API channel, while keeping simulation evidence separate from physical evidence. This is a staged engineering plan; a GitHub merge or a worker self-report is not proof of mining or earnings.

## Current implementation pieces

- `brain_v12/brain/bitcoin_worker_api.py`: authenticated heartbeat/status API. It stores the latest reports in process memory and marks worker telemetry as self-reported.
- `brain_v12/app.py`: mounts the worker router in the main Brain FastAPI application.
- `brain_v12/local_worker/bitcoin_worker_telemetry_agent.py`: polls an explicitly configured miner stats endpoint and forwards the reported values to Brain. It does not launch or control the miner.
- Required runtime configuration is external to source control. No secrets belong in Git.

## Priority improvements

### P0 — Safe connection and runtime readiness
1. Add a dedicated worker registration/identity record with a stable worker ID and owner authorization.
2. Keep `BRAIN_MINING_WORKER_API_TOKEN` in the runtime secret store; require HTTPS for Brain remote traffic and constant-time token comparison.
3. Add a readiness/status endpoint that distinguishes `API_READY`, `TOKEN_MISSING`, `WORKER_OFFLINE`, and `WORKER_REPORT_STALE`.
4. Add startup configuration validation and safe, redacted logs. Never print tokens or authorization headers.
5. Ensure the telemetry agent reads only a local miner stats endpoint unless the operator explicitly configures a remote HTTPS endpoint. Do not infer units or fabricate missing counters.
6. Add tests for missing/invalid tokens, malformed payloads, stale timestamps, future timestamps, worker isolation, and stale/offline transitions.

### P1 — Durable evidence and trust boundaries
1. Persist worker heartbeat history rather than keeping only the latest in-memory report.
2. Record evidence provenance and timestamps; label worker-reported hashrate/counters as self-reported.
3. Keep independent pool evidence separate: accepted shares, rejected shares, stale shares, pool identity, observation window, and source of proof.
4. Never claim earnings or payout without independently verifiable pool/accounting evidence.
5. Add bounded request sizes, rate limits, request IDs, audit events, and token rotation guidance.
6. Reject duplicate or out-of-order reports where sequence numbers or monotonic timestamps are available.

### P2 — Physical-worker operations
1. Provide an operator-controlled service unit or Termux startup guide for the telemetry agent.
2. Add bounded retry/backoff and a health status that does not hide persistent failures.
3. Detect hashrate collapse, stale telemetry, and share-rejection spikes; emit alerts without automatically changing pool, wallet, or miner configuration.
4. Make stop/restart actions explicit operator-approved actions; no arbitrary remote shell or code execution through the API.
5. Support CPU/GPU/ASIC workers as distinct worker classes only when each has a real, tested adapter and truthful hardware identity.
6. Measure actual resource use and temperatures only where the local driver/API supplies those values.

## Acceptance gates

- [ ] App imports and mounts the worker router.
- [ ] Running Brain OpenAPI lists both worker endpoints.
- [ ] Requests without a token and with a wrong token fail closed.
- [ ] Valid authenticated heartbeat from an owner-authorized physical worker is received over HTTPS.
- [ ] A fresh worker status shows the expected ID and a recent receive timestamp.
- [ ] Unit tests cover authentication, schema validation, stale data and isolation.
- [ ] Physical-worker data is never mixed with simulation records.
- [ ] Pool-side accepted-share evidence is independently captured before calling mining active.
- [ ] Earnings/payout claims require independent evidence.
- [ ] No paid infrastructure is provisioned automatically and no wallet/funds operation is performed.

## Master implementation prompt for Brain

You are Brain's Physical Worker Integration Engineer. Work in small, auditable changes in the existing repository. First inspect the current implementation and identify the actual FastAPI entry point, worker API, telemetry agent, tests, and deployment method. Preserve existing interfaces and simulation/physical evidence separation.

Implement the P0 items first, then P1 and P2 in separate commits. Do not claim a feature is complete merely because code exists. Add focused tests for every security boundary. Use environment variables or the runtime secret store for secrets; never write tokens to files tracked by Git, logs, issue bodies, or PR descriptions. Fail closed if authentication or HTTPS requirements are not met. Do not add arbitrary remote command execution, wallet access, mining-pool credential storage, or automatic spending.

The telemetry agent must read actual fields from a configured miner stats endpoint; do not invent hashrate, shares, hardware identity, or success. Report source provenance and timestamps. Worker-reported telemetry is not independent proof. Keep pool-accepted-share evidence and payout evidence as separate gates.

Before changing code, inspect current code and avoid duplicate modules. Make changes on a feature branch, create/update tests, and provide a concise implementation report with changed paths, test commands and results, exact remaining blockers, and links to the commit/PR. Do not merge automatically if the repository's required checks or review gates are unresolved. Do not deploy, start a miner, change a pool, use a wallet, or provision paid infrastructure without explicit operator approval.

## Known limitations to resolve before live use

- The API currently keeps the latest heartbeat in process memory; it is lost on restart and does not support cross-process workers.
- Worker API token setup and runtime deployment have not been verified on a live Brain instance.
- The telemetry agent has not yet been tested against a real miner stats endpoint.
- No physical worker heartbeat or independent pool-side accepted-share evidence has been observed here.
- No mining or payout success is claimed.
