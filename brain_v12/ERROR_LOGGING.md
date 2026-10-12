# Brain Error Logs & Traceability

The V1 error log subsystem stores append-only, structured JSON Lines at
`.brain/logs/errors.jsonl` by default. Override the location with
`BRAIN_ERROR_LOG_PATH` (use a persistent writable volume in deployments).

## Captured evidence

Each event includes UTC timestamp, event ID, severity, category, component,
source path, trace ID, message, exception type/traceback where available,
HTTP status, redacted context, and a repair lifecycle initialized to
`PENDING`. HTTP responses include `X-Brain-Trace-Id`; clients can supply
that header to correlate a request with its log event.

The ASGI middleware records uncaught exceptions and HTTP 5xx responses. The
protected API supports recent-event filtering and lookup by event ID:

- `GET /api/logs/errors?limit=100&severity=ERROR&component=fastapi`
- `GET /api/logs/errors/{event_id}`
- `POST /api/logs/errors/test` (writes a harmless diagnostic event)

All endpoints require the Brain control key. Request bodies and authorization
headers are not recorded. Secret-like fields are redacted before persistence.
Logs are local to the configured runtime volume; use persistent storage and
restricted access for production. This module does not claim that a repair
succeeded: it records evidence for later diagnosis and verification.
