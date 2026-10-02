# BRAIN Dيوان — Approval & Correspondence System

The Dيوان is Brain Cloud's human-governance inbox. It is the authoritative
system of record for human approvals. Email is a notification channel, not the
source of truth.

## Lifecycle

\`CREATED → PENDING → APPROVED | REJECTED | RETURNED\`

A worker must not treat a request as approved until a durable decision exists.

## Channels

1. Dيوان web inbox — authoritative.
2. Email — notification containing a link back to the Dيوان.
3. Future push channels — notifications only.

## Safety

- Opening an email never means approval.
- Silence never means approval.
- Approval never means PAYMENT_VERIFIED.
- An approval request does not itself send an external action.
- The record contains actor, decision, timestamp, note and evidence.
- Sensitive actions may require a second approval.
- Authenticated access is required for decisions.
- Ordinary operational work remains Brain/worker work after approval.

## Email

Email is enabled only when SMTP is explicitly configured:
\`BRAIN_SMTP_HOST\`, \`BRAIN_SMTP_PORT\`, \`BRAIN_SMTP_USERNAME\`,
\`BRAIN_SMTP_PASSWORD\`, \`BRAIN_SMTP_FROM\`.

Optional:
\`BRAIN_PUBLIC_BASE_URL\`, \`BRAIN_APPROVAL_LINK_SECRET\`.

If SMTP is not configured, Brain records the notification in its outbox and
does not claim that an email was sent.
