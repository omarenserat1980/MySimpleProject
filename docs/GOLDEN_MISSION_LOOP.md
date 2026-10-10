# Golden Mission Loop

## Purpose and safety boundary

The Golden Mission controller stores mission state durably in SQLite and exposes authenticated control endpoints. It is a mission tracker and reminder loop, not a general-purpose privileged executor. It does not start VMs, modify devices, publish media, spend money, or deploy infrastructure.

A mission can close only when the evidence store contains evidence for that same mission, the caller supplies the matching evidence ID and SHA-256, and the evidence store verifies the stored hash. The evidence payload must identify the current attempt with `attempt_number` (initial attempt is `1`; each recorded retry advances it), mark the objective and acceptance as passed, and include exactly one passing result for every declared acceptance criterion. Evidence from an earlier attempt or evidence that omits, duplicates, or substitutes acceptance criteria is rejected.

## API

All routes require the X-Brain-Control-Key header matching the server's BRAIN_CONTROL_KEY.

- POST /api/golden-missions — create a mission with title, objective, non-empty acceptance, estimate_minutes, update_minutes, and max_attempts.
- GET /api/golden-missions/due — inspect missions whose next update is due.
- GET /api/golden-missions/{mission_id} — inspect a mission and its event/evidence history.
- POST /api/golden-missions/{mission_id}/start — start tracking.
- POST /api/golden-missions/{mission_id}/permission-required — pause for a named permission and attempt to notify the configured recipient.
- POST /api/golden-missions/{mission_id}/permission-grant — record an explicit grant with permission name and approver identifier.
- POST /api/golden-missions/{mission_id}/checkpoint — record a progress checkpoint and optionally revise the estimate.
- POST /api/golden-missions/{mission_id}/retry — record a failed attempt; the mission becomes BLOCKED at the configured retry limit.
- POST /api/golden-missions/{mission_id}/close — close only with evidence ID and SHA-256 that pass the verification gates.

## Opt-in recurring reminders

The background reminder worker is disabled by default. To enable it on a long-running Brain process, set:

- BRAIN_GOLDEN_MISSION_SCHEDULER_ENABLED=true
- BRAIN_GOLDEN_MISSION_POLL_SECONDS=300 (minimum 30 seconds)

The worker checks due missions, attempts an email reminder, records the result, and advances the next-update time to avoid repeated messages on every poll. It never executes the mission objective. It is started/stopped with the FastAPI application lifecycle. If the process is stopped, reminders pause and resume when the application starts again.

Email settings:

- BRAIN_SMTP_HOST
- BRAIN_SMTP_PORT (default 587)
- BRAIN_SMTP_FROM
- BRAIN_MISSION_EMAIL_TO
- BRAIN_SMTP_STARTTLS (default 1)
- Optional authentication: BRAIN_SMTP_USERNAME, BRAIN_SMTP_PASSWORD

When the email settings are absent or delivery fails, the event log records the failure. The API does not claim the email was sent.

## Persistence

- Mission database: BRAIN_GOLDEN_MISSION_DB; default brain_v12/golden_missions.sqlite3.
- Evidence database is shared with the existing EvidenceStore through BRAIN_EVIDENCE_DB.
- Back up both databases using the deployment's normal checkpoint/backup process. Do not commit runtime database files or secrets.

## Validation

The dedicated workflow compiles the changed modules and runs the Golden Mission and Synthetic Customer regression suites. A green CI result validates code/tests in GitHub Actions; it does not prove that the user's cloud host, SMTP provider, or device agents are running.
