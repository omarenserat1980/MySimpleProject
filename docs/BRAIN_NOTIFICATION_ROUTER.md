# Brain Notification Router

The Brain Notification Router is the operational notification layer above provider-specific adapters such as AgentMail.

## Policy

- ERROR and CRITICAL are notification-eligible by default.
- INFO and WARNING do not generate email by default.
- The same event type, source, and fingerprint produce one deterministic event ID and are not emailed again after a verified send.
- Missing recipient configuration fails closed.
- Provider failures are recorded as SEND_FAILED and never reported as successful.
- Secrets and recipient addresses are not written to source or evidence.
- A send is verified only when the email adapter returns both message_id and thread_id.

## Evidence

Default evidence path: .brain_state/notifications.jsonl

Records contain operational metadata such as event ID, severity, status, timestamp, and provider message/thread IDs.

## Environment

- AGENTMAIL_API_KEY — secret.
- BRAIN_EMAIL_INBOX_ID — AgentMail inbox identifier.
- BRAIN_ALERT_TO — recipient secret.
- BRAIN_NOTIFICATION_EVIDENCE — optional evidence path.

## Integration

CI failure, recovery, release-gate, and other high-value operational events should call this router rather than sending email directly. The router is provider-neutral so another free/open-source or Brain-owned adapter can replace AgentMail.
