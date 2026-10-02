# BRAIN Customer Communications Hub

## Purpose

Provide a unified, evidence-first communication layer between Brain and customers.

The communication channel is not the authoritative business record. Business-relevant messages are registered in Diwan and linked to a customer, case, request, quote, approval, delivery, or payment record.

## Channels

- CUSTOMER_PORTAL
- EMAIL
- WEB_CHAT
- API
- MESSAGING_ADAPTER (future/provider-dependent)

## Lifecycle

`DRAFTED -> QUEUED -> SENT -> DELIVERED -> ACKNOWLEDGED -> CLOSED`

Exception states:

`FAILED, CANCELLED, BOUNCED, LEGAL_HOLD`

## Rules

1. Customer-facing identity uses the approved Brain/entity identity; private operator addresses are never exposed.
2. Service consent, marketing consent, and analytics consent remain separate.
3. A customer message is not automatically customer approval.
4. Commercial acceptance must pass the applicable customer-consent and operator-authority gates.
5. Payment verification is never inferred from a message or uploaded receipt alone.
6. Important inbound/outbound messages are captured into Diwan with content hash and provenance.
7. Email/chat delivery is evidence about transport, not proof of contractual acceptance unless the applicable agreement and evidence establish acceptance.
8. Failed delivery creates a retryable operational task and does not become a successful communication.
9. Legal hold prevents deletion of the authoritative record.
10. The system must never report SENT/DELIVERED without transport evidence.

## Target flow

Customer -> Channel Adapter -> Communications Hub -> Diwan/Case File -> Supervisor -> Worker -> Response -> Channel Adapter

The next integration layer should expose authenticated API endpoints for conversation creation, message registration, thread retrieval, and outbound queueing.
