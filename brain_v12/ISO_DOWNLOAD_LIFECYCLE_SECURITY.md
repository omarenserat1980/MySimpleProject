# ISO Download Lifecycle, Authorization, Storage and Cleanup Contract

**Scope:** source, local tests, and documentation only. The proposed API routes are not registered by this change.

## Existing implementation boundary

- `brain/iso_download_store.py` owns persisted task metadata, state transitions, transition history, owner-scoped reads, worker leases, and server-derived storage paths.
- `brain/iso_download_policy.py` provides exact-host source URL checks and SHA-256 verification. It deliberately does not perform downloads.
- The existing shared control-plane key is not a per-user identity provider and cannot by itself distinguish `viewer`, `operator`, and `administrator`. Do not expose download endpoints until the trusted principal/role provider is identified and enforced.
- SQLite metadata does not prove that a worker survives process restart. Resumption requires a supervised worker plus storage whose persistence is guaranteed by deployment configuration.
- A writable directory is not evidence of durable storage. Do not assume Render Free retains ISO files after restart or redeploy.

## State machine and transitions

The canonical transition table is `TRANSITIONS` in `brain/iso_download_store.py`; callers must use `DownloadStore.transition`, never directly update a task's state.

Expected edges:
- CREATED → VALIDATING
- VALIDATING → QUEUED | FAILED | CANCEL_REQUESTED
- QUEUED → CONNECTING | CANCEL_REQUESTED
- CONNECTING → DOWNLOADING | RETRY_WAIT | CANCEL_REQUESTED
- DOWNLOADING → PAUSE_REQUESTED | RETRY_WAIT | VERIFYING | CANCEL_REQUESTED
- PAUSE_REQUESTED → PAUSED | CANCEL_REQUESTED | INTERRUPTED
- PAUSED → QUEUED | CANCEL_REQUESTED | EXPIRED
- RETRY_WAIT → CONNECTING | FAILED | CANCEL_REQUESTED | INTERRUPTED
- VERIFYING → COMPLETED | FAILED | CANCEL_REQUESTED | INTERRUPTED
- CANCEL_REQUESTED → CANCELLED | INTERRUPTED
- INTERRUPTED → RECOVERING
- RECOVERING → PAUSED | QUEUED | FAILED | CANCEL_REQUESTED
- COMPLETED | CANCELLED | FAILED → EXPIRED
- EXPIRED has no outgoing edges.

Transitions must atomically record old/new state, timestamp, reason, and request ID without secrets. A task can hold at most one worker lease. Leases expire after a configurable TTL (120 seconds by default); recovery may reclaim an expired lease. The store now offers monotonically increasing fencing tokens (`acquire_worker_token`), token-specific renewal (`renew_worker_lease`), and a live-token check (`assert_worker_lease`). A worker must stop writing when renewal/check fails, and the token must be enforced at every file-write and final-promotion boundary. These are storage primitives only: no supervised downloader currently calls them, and ordinary filesystem writes are not automatically fenced, so crash recovery is not yet implemented end-to-end. The legacy `acquire_worker`/`renew_worker` methods remain for compatibility and do not themselves give callers a fencing token. Repeated pause/resume/cancel requests must return a stable idempotent result. Terminal states must never return to active states. A recovery supervisor must explicitly mark interrupted tasks; do not fabricate a transition from a state not allowed by the store.

## Authentication and authorization gate

- Use the current control-plane authentication guard for existing administrative APIs; do not introduce a hardcoded secret.
- Task ID, device ID, URL, and network location are not identities.
- Future API handlers must resolve a trusted principal and role on every request and enforce task ownership on every read or mutation.
- Role matrix: viewer = read only owned/assigned metadata; operator = create/pause/resume/cancel owned/assigned tasks; administrator = manage allowlist and resource limits but cannot bypass source or integrity rules.
- Missing/invalid credentials should produce 401; authenticated but forbidden requests should produce 403 without revealing another user's task existence.
- Do not register download routes until user identity, role claims, ownership, request limits, and error response conventions are connected to a real trusted provider.

## Source policy and SSRF

- HTTPS only, exact hostname allowlist from `BRAIN_ISO_ALLOWED_HOSTS`, port 443 only, no URL credentials, wildcard entries, or fragments.
- Reject non-global DNS answers. Empty allowlist denies all remote sources.
- The policy helper's DNS check alone does not stop DNS rebinding. A future downloader must pin validated addresses to the actual socket connection while retaining TLS hostname validation, disable ambient proxy behavior unless explicitly governed, and revalidate each redirect before following it.
- Never accept an output path from the client. The server derives paths under its configured storage root.

## Storage, durability and safe cleanup

- Separate `metadata/`, `partial/`, `completed/`, and `quarantine/` under a server-configured root. Keep binaries out of Git and static web roots.
- Write to a task-owned temporary file. Promote to `completed` only after expected-size checks and a trusted SHA-256 digest pass; otherwise do not claim integrity.
- Before declaring PAUSED, flush the partial data and persist resume metadata atomically as supported by the filesystem.
- A resumable task must be refused with `PERSISTENT_STORAGE_REQUIRED` unless the caller declares persistent storage. The current `persistent=True` argument is a caller assertion, not an independent mount/durability probe; deployment integration must verify the actual storage contract before passing it.
- Cancellation never deletes completed media or VM-linked files. Failure or interruption alone does not authorize deletion.
- Delete only a task-owned partial file when no worker/recovery lease can write to it; re-check resolved paths remain under the partial root and reject symlinks/path traversal. Never use wildcard deletion or user-provided paths.
- Do not run global cleanup on startup. Record `CLEANED`, `RETAINED`, or `CLEANUP_FAILED`. Retention applies only to inactive metadata and unreferenced partials; never automatically delete completed media, quarantine, or VM disks.
- No real ISO download, device access, paid resource, production mutation, or deployment is part of this change.

## Proposed API contracts (not registered)

- POST `/api/brain/iso-downloads`
- GET `/api/brain/iso-downloads/{download_id}`
- POST `/api/brain/iso-downloads/{download_id}/pause`
- POST `/api/brain/iso-downloads/{download_id}/resume`
- POST `/api/brain/iso-downloads/{download_id}/cancel`

Standard error envelope: `{"error":{"code":"...","message":"Safe public message","request_id":"..."}}`.
Required stable codes include `UNAUTHORIZED`, `FORBIDDEN`, `INVALID_STATE_TRANSITION`, `SOURCE_NOT_ALLOWED`, `SOURCE_CHANGED`, `RANGE_NOT_SUPPORTED`, `INTEGRITY_CHECK_FAILED`, `PERSISTENT_STORAGE_REQUIRED`, `INSUFFICIENT_STORAGE`, `TASK_NOT_FOUND`, `TASK_CONFLICT`, `RETRY_LIMIT_EXCEEDED`, and `CLEANUP_FAILED`. Never include secrets, local paths, or infrastructure details.

## Acceptance evidence

The policy tests cover exact allowlist parsing, rejection of unsafe URL forms and private DNS answers, DNS failure, SHA-256/size verification, and symlink rejection. They do not prove API role enforcement, actual network transport DNS pinning, HTTP Range behavior, Render durability, worker restart recovery, cleanup race resistance, or Windows Server boot. Those remain NOT RUN / NOT IMPLEMENTED until the related integration exists.
