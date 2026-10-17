# Brain Durable Task Queue Contract

Status: design contract only. This document does not enable command execution.

## Required safety properties

- **Durability:** an accepted task survives process restart. A successful HTTP response must not be sent until the task record is committed to durable storage.
- **Idempotency:** every submission carries an idempotency key scoped to the authenticated principal. Repeating the same key and same canonical payload returns the original task; reusing it with a different payload returns a conflict.
- **Bounded task schema:** accept only a versioned allow-list of named task types with validated, size-limited JSON arguments. Never accept arbitrary shell commands, scripts, executable paths, or unrestricted URLs.
- **Authorization:** authenticate the caller and authorize each task type separately. Missing or invalid credentials fail closed.
- **Leases:** use a unique lease token, bounded TTL (greater than zero and no more than 24 hours), attempt counter, and compare-and-set transitions. A stale worker must not complete a task after its lease has expired or been replaced.
- **Auditability:** record task ID, idempotency key hash, principal, task type, timestamps, state transitions, attempt count, worker ID, and sanitized failure codes. Never log credentials or secret task arguments.
- **Evidence:** store an integrity-checked result manifest with task ID, executor version, start/end timestamps, outcome, and artifact digests. A task marked successful must reference a persisted result.
- **Recovery:** on startup, reconcile queued tasks and expired leases without silently marking interrupted work successful. Retry only task types declared retry-safe; use a bounded retry policy.
- **Isolation:** use a single-writer transaction or database transaction for task insertion, idempotency lookup, lease acquisition, and state changes. A JSON file with only in-process locking is not sufficient for multi-process production use.
- **Operational boundaries:** queue readiness must be reported separately from worker readiness. Queue unavailability means task submission fails closed. Do not imply a task ran merely because it was accepted.

## Canonical state machine

`accepted -> queued -> leased -> running -> succeeded`

Alternative terminal or recovery transitions:

- `queued -> cancelled` only when cancellation policy authorizes it.
- `leased/running -> queued` after lease expiry only if retry-safe and attempts remain.
- `leased/running -> failed` when retries are exhausted or a non-retryable error occurs.
- `running -> succeeded` only after result/evidence is durably committed and the current lease token still matches.

Illegal transitions must be rejected, not repaired silently. Terminal states are immutable except for a separate audited administrative correction.

## Minimum implementation sequence

1. Add versioned task, result, idempotency, and audit records with schema validation.
2. Choose durable storage supported by the deployment environment and document backup/recovery behavior.
3. Implement atomic submission and idempotency conflict handling.
4. Implement transactional lease acquire/renew/complete and expiry recovery.
5. Add self-tests for restart persistence, duplicate submissions, payload mismatch, stale lease completion, concurrent acquisition, corrupt records, and interrupted writes.
6. Keep `POST /api/brain/command` returning `501 COMMAND_EXECUTION_NOT_CONNECTED` until the full queue and a constrained executor pass tests.
7. Enable only a harmless allow-listed task in a non-production environment; capture independent evidence before any production enablement.

## Explicit non-goals

This contract does not authorize arbitrary code execution, deployment changes, live mining, publishing, purchases, or other financial actions. Real mining and revenue require independent pool/account evidence; CI success and simulated results do not qualify.
