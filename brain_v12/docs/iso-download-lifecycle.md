# Brain V12 ISO download lifecycle — implementation notes

## Scope and status

The lifecycle store is a first implementation slice, not a complete download service. It is deliberately not registered as an HTTP router and does not make outbound network requests. Do not expose ISO downloads until the remaining integration and security gates below are implemented and verified.

Source: `brain_v12/brain/iso_download_store.py`
Tests: `brain_v12/tests/test_iso_download_store.py`

## State-transition contract

The store is the only owner of state transitions. `transition()` uses a SQLite `BEGIN IMMEDIATE` transaction, performs a conditional state update, and appends the transition event in the same transaction. Unknown edges return `INVALID_STATE_TRANSITION` without modifying state or history. Task identifiers are random and are never recycled by this store.

| Current | Allowed next state(s) |
|---|---|
| CREATED | VALIDATING |
| VALIDATING | QUEUED, FAILED, CANCEL_REQUESTED |
| QUEUED | CONNECTING, CANCEL_REQUESTED |
| CONNECTING | DOWNLOADING, RETRY_WAIT, CANCEL_REQUESTED |
| DOWNLOADING | PAUSE_REQUESTED, RETRY_WAIT, VERIFYING, CANCEL_REQUESTED |
| PAUSE_REQUESTED | PAUSED, CANCEL_REQUESTED, INTERRUPTED |
| PAUSED | QUEUED, CANCEL_REQUESTED, EXPIRED |
| RETRY_WAIT | CONNECTING, FAILED, CANCEL_REQUESTED, INTERRUPTED |
| VERIFYING | COMPLETED, FAILED, CANCEL_REQUESTED, INTERRUPTED |
| CANCEL_REQUESTED | CANCELLED, INTERRUPTED |
| INTERRUPTED | RECOVERING |
| RECOVERING | PAUSED, QUEUED, FAILED, CANCEL_REQUESTED |
| COMPLETED | EXPIRED |
| CANCELLED | EXPIRED |
| FAILED | EXPIRED |
| EXPIRED | none |

Repeated state-changing API commands still need route-level idempotency policy. The primitive supports a same-state idempotent transition without adding a duplicate event, but it is not a substitute for authenticated operation-specific pause/resume/cancel handling.

## Storage layout and persistence

The configured root is divided into `metadata/`, `partial/`, `completed/`, and `quarantine/`. SQLite uses WAL and FULL synchronous mode for the metadata database. These settings improve transactional durability but do not prove that the underlying filesystem survives host replacement, redeploy, or provider maintenance.

The caller must explicitly supply whether storage has been established as persistent. When `resumable=True` and that flag is false, task creation returns `PERSISTENT_STORAGE_REQUIRED`. A write probe alone must never be used to set the flag to true. The deployment integration must determine the storage contract from trusted environment/provider configuration.

Files are not downloaded, promoted, quarantined, or deleted by this module. Cancellation therefore does not delete completed artifacts. Cleanup outcomes are recorded as `CLEANED`, `RETAINED`, or `CLEANUP_FAILED`, but a future cleanup executor must verify filesystem effects before recording success.

## Authentication and API integration gate

Brain currently has a shared control-key helper in `brain_v12/brain/control_auth.py`. It expects `BRAIN_CONTROL_KEY` and `X-Brain-Control-Key`; it returns 503 when unconfigured and 403 when missing/incorrect. This helper does not itself provide the requested viewer/operator/administrator roles or per-task ownership model. Do not expose this store through routes until the existing authentication model is reconciled with the API contract. Missing authentication must not be disguised as role authorization.

The following proposed routes are not implemented by this change:
- `POST /api/brain/iso-downloads`
- `GET /api/brain/iso-downloads/{download_id}`
- `POST /api/brain/iso-downloads/{download_id}/pause`
- `POST /api/brain/iso-downloads/{download_id}/resume`
- `POST /api/brain/iso-downloads/{download_id}/cancel`

## Mandatory remaining gates before route exposure

1. Implement and test role × operation policy, authentication failure status semantics, and owner-scoped reads/control.
2. Implement a strict source allowlist and SSRF defenses, including DNS resolution/address checks at connection time, redirect validation, and safe handling of DNS rebinding. Do not accept arbitrary URLs.
3. Implement a bounded downloader with connect/read/total timeouts, size and free-space limits, retry backoff, safe Range/206/Content-Range validation, ETag/Last-Modified consistency checks, and optional trusted SHA-256 verification.
4. Implement crash recovery by reconciling actual partial-file size and source identity; saved byte counters alone are not sufficient.
5. Implement atomic promotion into `completed/` only after verification, quarantine on integrity/source mismatch, and path/symlink/TOCTOU-safe cleanup. No broad startup cleanup.
6. Integrate background workers with durable leases and lease expiry/recovery. Current worker leases prevent duplicate concurrent acquisition but are not yet a full renewable lease/fencing-token system.
7. Add FastAPI test-client tests with a local-only HTTP fixture for route authentication, redirects/SSRF, pause/resume/cancel races, partial responses, hash mismatch, disk exhaustion, restart recovery, and UI disconnect independence.
8. Run the new tests and existing regression suite in a controlled checkout. No result is PASS until the command has actually run and its output is recorded.

## Current error codes

The store uses `INVALID_STATE_TRANSITION`, `PERSISTENT_STORAGE_REQUIRED`, `TASK_NOT_FOUND`, `TASK_CONFLICT`, `INVALID_REQUEST`, and `INVALID_STORAGE_PATH`. Route-level errors must be normalized to the project API contract without exposing filesystem paths, credentials, or internal exceptions.
