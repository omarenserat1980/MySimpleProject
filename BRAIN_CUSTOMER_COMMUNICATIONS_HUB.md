# BRAIN Customer Communications Hub — Production Baseline

## Objective
Make every customer interaction traceable, timely, consent-aware and recoverable without exposing the private operator identity.

## Channels
- Customer Portal
- Email adapter
- Web Chat
- API
- Future messaging adapters

The Hub is the communications system of record for transport state; Diwan remains the authoritative business-record/archive layer.

## Customer experience contract
1. One customer identity across channels.
2. One thread/case reference across the conversation.
3. Every outbound message has a purpose and applicable consent scope.
4. Every important inbound/outbound message is hash-protected and linked to the relevant case/request.
5. No `SENT` or `DELIVERED` claim without transport evidence.
6. No customer message is treated as commercial acceptance unless the consent/approval gate establishes it.
7. Private operator email is never exposed to customers.

## Reliability
- Durable atomic message storage.
- Idempotency keys prevent duplicate sends.
- Retryable FAILED/BOUNCED states.
- Attempt counter and last error are preserved.
- Provider adapters must return transport evidence.
- External provider outage must not corrupt the authoritative message record.

## Service discipline
Each message has:
- priority: LOW/NORMAL/HIGH/URGENT
- SLA in minutes
- assigned actor/team
- escalation state
- immutable content hash
- lifecycle events

Overdue messages become operational escalations; they do not silently disappear.

## Lifecycle
`DRAFTED -> QUEUED -> SENT -> DELIVERED -> ACKNOWLEDGED -> CLOSED`

Exceptions:
`FAILED, CANCELLED, BOUNCED, LEGAL_HOLD`

## Commercial safety
Service consent, marketing consent and analytics consent remain separate.
Payment verification is never inferred from email/chat/receipt uploads.
Commercial actions pass the operator-authority and customer-consent gates.

## Target operating loop
Customer -> Channel Adapter -> Communications Hub -> Diwan/Case File -> Supervisor -> Worker -> Response -> Channel Adapter -> Evidence -> Metrics

## Required production adapters
- Email provider with verified sender identity and delivery/bounce evidence.
- Portal/web-chat transport.
- Optional messaging provider adapters.
- Webhook ingestion for provider delivery/bounce events.

Until an adapter is connected, messages remain `QUEUED`/connector-pending; the system must never simulate delivery.

## Operational metrics
- first-response time
- SLA compliance
- delivery/bounce/failure rate
- unresolved conversations
- overdue escalations
- customer consent coverage
- duplicate-send prevention
- customer-to-quote conversion
- quote-to-payment verification conversion

## Security
Authenticated access, least privilege, audit logging, retention/legal hold and redaction of secrets/payment credentials are mandatory.
