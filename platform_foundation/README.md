# Platform Foundation

This directory is the independent Base Expansion foundation. It intentionally does not import `brain_v12`.

## Verified base contract (phase 4-3)
- Runtime start/stop and health reporting.
- State set/get/snapshot/restore.
- Job registration/execution and explicit failure capture.
- Append-only, defensive evidence events.

## Phase 4-4 security, failure, and recovery slice
- Explicit actor/action permission grants; ungranted protected jobs are denied by default.
- Failure classification records retryability but never retries automatically.
- Integrity-checked state checkpoints and restore events.
- Defensive state copies prevent callers from mutating stored values through snapshots.

## Scope and limits
The permission grants, failure records, evidence ledger, and checkpoints are in-memory only. Checkpoints are JSON-compatible state snapshots, not durable backups. This slice does not provide persistent identity, distributed authorization, encrypted storage, process restart recovery, or production disaster recovery. Those capabilities require separate design and verification.
