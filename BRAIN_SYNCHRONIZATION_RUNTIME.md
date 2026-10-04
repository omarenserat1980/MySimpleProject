# Brain Synchronization Runtime v1

## Purpose
Turn the deterministic synchronization core into an offline-first runtime primitive for the Brain Termux Emulator, cloud replicas, and future Control Plane adapters.

## Guarantees
- Durable local queue stored as JSONL with atomic replacement.
- Duplicate event IDs are ignored.
- A queue item is acknowledged only after the supplied transport accepts it.
- Failed delivery remains replayable.
- Heartbeats carry a monotonic per-agent sequence and become stale after a configurable TTL.
- Reconciliation emits before/after state digests, queue counters, audit-chain validity, and an evidence digest.
- The runtime itself performs no payment, publishing, withdrawal, contract, or other external side effect.

## Runtime flow
Local SyncStore -> DurableSyncQueue -> transport boundary -> Cloud SyncStore -> digest/audit verification

During connectivity loss, events remain PENDING or FAILED. On reconnect, replay is idempotent and may safely be retried.

## Emulator contract
The existing brain_v12/tools/brain_emulator_agent.py remains the bounded executor. Its heartbeat and poll/report APIs are unchanged. The runtime layer is intentionally transport-agnostic so the emulator can adopt it without granting arbitrary shell or network authority.

## Evidence
A reconciliation result must contain:
- queue sent/acked/failed counts
- local digest
- remote digest before/after
- audit-chain validity
- 64-character evidence digest

RECONCILED is valid only when no delivery failed. PARTIAL is not success.

## Next integration gate
The next gate is wiring this runtime into the device/task state adapter so task transitions and evidence references produce sync events automatically, followed by an end-to-end disconnect/reconnect workflow test.