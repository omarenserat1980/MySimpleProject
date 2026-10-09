# ADR: Brain Chat Identity, Device Pairing, and Session Isolation

- Status: In progress; backend device-token enforcement and focused tests are implemented on the PR branch; rollout is not complete.
- Date: 2026-10-10
- Scope: `brain_v12/brain/chat_session_api.py`, `chat_session_store.py`, and the Brain Chat web client.

## Context

The current Chat API accepts client-supplied `account_id` values and session IDs. An account ID is a label, not proof of identity. Session read/write endpoints must not infer ownership from a caller-provided identifier. In particular, listing sessions without an account filter must never expose all sessions.

The existing static web client cannot safely hold a server secret. The industrial-client key is scoped to a different integration and must not be repurposed as end-user authentication without a separate review.

## Proposed default

Use a self-hosted, free, server-side device-pairing model. Do not add a paid identity provider as a requirement.

1. **Trusted bootstrap:** An operator-controlled local CLI or equivalent trusted server-side procedure creates a short-lived, single-use pairing code. Do not expose an unauthenticated public endpoint that can mint arbitrary accounts or pairing codes.
2. **Pairing:** The user enters the one-time code on a device. The server validates expiry, single use, attempt limits, and scope; it then issues a high-entropy device credential. Never return the pairing code or credential in logs.
3. **Credential storage:** Store only a cryptographic hash of each device credential server-side. The browser stores its credential using the narrowest practical storage model; document the XSS risk and apply CSP/output-encoding protections. Never embed a shared server secret in HTML or JavaScript.
4. **Identity source:** Middleware validates the credential and derives the account and device identity from the server-side credential record. Client-supplied `account_id` is not authoritative; reject mismatches or ignore it after explicit compatibility review.
5. **Authorization:** Every session operation (create, list, get, sync, memory read/write, compact, and send-message) enforces account ownership. Device-level revocation is checked on every authenticated request. Missing or invalid credentials fail closed with 401; valid credentials attempting cross-account access receive 403 or a non-enumerating 404 policy applied consistently.
6. **Listing:** An unauthenticated or unscoped list request must never return all sessions. The account scope comes from the authenticated principal, not a query parameter.
7. **Multi-device sync:** Pair each device to the same account through the trusted pairing flow. Preserve existing event IDs, cursor semantics, idempotency, and conflict behavior; never weaken authorization to retain sync.
8. **Revocation and audit:** Support revoking one device and all account devices. Audit credential issuance, pairing failures (without secrets), and revocation, with rate limits and bounded retention.
9. **Migration:** Existing sessions need an explicit ownership/migration policy. Do not silently assign legacy sessions to whichever account first requests them. Keep migration fail-closed and provide a reviewed operator recovery path.
10. **Transport:** Require HTTPS whenever traffic leaves loopback/trusted local transport. Do not treat CORS, a UUID, a device ID, or an account ID as authentication.

## Required tests / acceptance gates

- No credential, malformed credential, expired credential, and revoked credential are rejected.
- Pairing codes expire, are single-use, are scoped, and are rate-limited.
- User A cannot list, read, sync, compact, send messages to, or read/write memory for User B's session.
- Omitting `account_id` cannot return sessions belonging to other accounts.
- Client-supplied account/device identifiers cannot override the authenticated principal.
- A paired second device can sync only the same account's sessions; revoking either device takes effect immediately.
- Legacy/unowned sessions remain inaccessible until an explicit migration is completed.
- Existing chat idempotency, wildcard-ID regression, and sync cursor tests continue to pass.
- Security tests run in CI and fail closed; no test relies on a public hard-coded credential.

## Rollout plan

1. The threat model and acceptance gates are documented here.
2. Implemented on this branch: server-side device-token hash storage, token expiry/revocation, and local operator issuance via `python -m brain_v12.brain.chat_identity --db brain_v12.db issue --account <account-id> --device-label <device-label>`. The raw token is printed once.
3. Implemented on this branch: bearer authentication and account ownership checks across session create/list/get, sync, memory read/write, compact, and message endpoints. The server ignores caller-supplied account IDs and device IDs for authorization.
4. The web client now attaches the per-device token; it asks for the token once and stores it in localStorage. This has an XSS exposure tradeoff and requires careful deployment of CSP and output encoding.
5. Focused tests now cover missing/revoked credentials and cross-account access; full API tests, full pytest, and CI results must still be verified.
6. Legacy sessions without an account owner remain inaccessible to authenticated accounts until an explicit migration/recovery process is defined. Keep this change in a separate PR; do not merge until checks pass and migration behavior is reviewed.

## Non-goals

- No paid identity provider dependency.
- No reuse of the industrial-client secret or control-plane token as a browser credential.
- No assumption that a public static client can keep a shared secret.
- No claim that session isolation is fixed until implementation and negative tests prove it.
