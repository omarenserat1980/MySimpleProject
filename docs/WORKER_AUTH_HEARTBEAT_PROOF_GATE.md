# Worker Authentication and Live Heartbeat Proof Gate

## Purpose

Keep worker authentication, heartbeat liveness, task execution, Bitcoin mining, and revenue as separate evidence gates. Passing unit tests or CI is not proof that a physical device is online.

## Evidence classes

- `REGISTERED`: an inventory record exists. This is not an online claim.
- `AUTHENTICATED`: a request reached the authenticated device endpoint with a valid credential for the resolved agent ID.
- `HEARTBEAT_LIVE`: the server received an authenticated heartbeat and its server-side receipt time is within `TERMUX_AGENT_TTL_SECONDS`.
- `TASK_EXECUTION_VERIFIED`: a live worker claimed a task, returned a result, and the server verified the result against task-specific criteria.
- `BITCOIN_MINING_VERIFIED`: separate pool/session evidence, measured hashrate, and accepted shares are present.
- `REVENUE_VERIFIED`: a trustworthy wallet/pool/payment record confirms receipt of funds.

## Required safeguards

1. Per-agent credentials must be used for real-device evidence. A shared key may establish legacy API access but is weaker evidence of device identity.
2. The server, not worker-supplied metadata, timestamps heartbeat receipt. Metadata such as `reality=REAL` is only a claim and must never promote a node to physical-device status.
3. A heartbeat must pass `require_device_agent` / `DeviceBridge.authenticate` before the server records it.
4. The online state expires after the configured TTL. A database row or historical heartbeat is not current liveness.
5. Simulation, CI, emulators, and virtual nodes remain separate from physical-device counts.
6. Record agent ID, authentication mode, server receipt time, TTL, source run, and evidence reference in the operational report. Never store raw credentials in evidence.
7. Do not mark mining or revenue verified from a worker heartbeat or a passing software test.

## Acceptance test interpretation

The tests in `brain_v12/tests/test_device_bridge.py` check credential matching and heartbeat-state behavior separately. They are software tests, not an end-to-end physical-device attestation. A live-device claim additionally requires a fresh authenticated request from the actual Termux agent and inspectable server-side evidence.

## Live verification sequence

1. Confirm the agent's per-agent credential is configured on the server and device without printing the secret.
2. Send an authenticated heartbeat from the real Termux process using `X-V12-Agent-Id` and `X-V12-Agent-Key`.
3. Read `/api/device/agent-status/{agent_id}` using the same agent identity and verify `online=true`, `age_seconds <= ttl_seconds`, and a fresh server receipt.
4. Wait longer than the TTL without heartbeats and confirm the agent becomes `STALE`.
5. Enqueue a harmless allowlisted task, observe the real agent poll and claim it, then verify the returned result and evidence reference.
6. Save timestamps and sanitized responses. If the live request or task result is unavailable, report `NOT_VERIFIED`, not success.
