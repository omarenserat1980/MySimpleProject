# Brain Email Gateway

## Purpose

Brain uses a provider-neutral outbound email boundary. AgentMail is the first
adapter and may be replaced or supplemented by other providers without
changing business logic.

## Runtime contract

Required secret:
- `AGENTMAIL_API_KEY` — GitHub Actions/production secret only.

Required non-secret configuration:
- `BRAIN_EMAIL_INBOX_ID` — AgentMail inbox identifier.
- `BRAIN_ALERT_TO` — recipient(s), supplied by deployment configuration.

The gateway never stores API keys in source, evidence artifacts, logs, issues,
or public documentation.

## Verification

A successful AgentMail API response must contain both `message_id` and
`thread_id`. A transport success without those identifiers is not treated as
verified delivery.

## Security

- Never print the API key.
- Never commit the API key.
- Keep personal recipient addresses out of source and public artifacts.
- Rotate/revoke the AgentMail key if it is exposed.
- External email is an outbound side effect and remains subject to Brain's
  permission and governance rules.
