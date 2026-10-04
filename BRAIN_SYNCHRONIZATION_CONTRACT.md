# Brain Synchronization Contract v1.0

## Purpose
Brain replicas (Cloud, BRAIN Termux Emulator/device agents, and future workers) must converge without silently overwriting newer state.

## Rules
1. Canonical identity — every logical record has a stable key.
2. Monotonic revision — every successful change increments that record's revision.
3. Idempotency — re-delivering the same event ID has no additional effect.
4. Optimistic concurrency — a write can declare the revision it observed; mismatches become explicit conflicts.
5. No accidental last-writer-wins — an older revision cannot overwrite newer local state.
6. Tombstones — deletes remain as durable records so offline replicas cannot resurrect deleted state.
7. Replayable event feed — replicas synchronize by replaying events; transport is separate from state logic.
8. Evidence — snapshots expose deterministic digests and the event chain is auditable.
9. Offline-first — devices may queue changes and replay them later; duplicate delivery is safe.
10. Side-effect boundary — synchronization changes state only. Publishing, payments, withdrawals, applications, and other external effects remain authorization-gated.

## Brain topology
Brain Cloud <-> Sync Store <-> device/emulator <-> local queue

GitHub remains the project source of truth. Runtime state synchronization is separate from Git source synchronization.

## Initial integration targets
- Control Plane job/task state
- Device agent heartbeats and offline queue
- Memory/event/audit state
- Evidence/artifact indexes

## Verification
Tests must demonstrate duplicate-event idempotency, stale-write rejection, offline convergence, durable deletes, deterministic snapshot digests, and audit-chain integrity.
