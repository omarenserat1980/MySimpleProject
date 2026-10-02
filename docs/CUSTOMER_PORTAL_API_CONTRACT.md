# Customer Portal API Contract

## POST /api/customers

Creates a customer request only. It must not create a contract, invoice, payment,
or external communication.

Request:
{
  "display_name": "string",
  "service": "string",
  "need": "string",
  "marketing_consent": false
}

Response should include:
- request_id
- status
- lifecycle_state
- consent_state
- evidence_state

Initial lifecycle state: DISCOVERED.
Initial evidence state: READY_FOR_REVIEW when required fields are present.

## GET /api/customers/{request_id}

Returns the evidence-backed request state.

## POST /api/customers/{request_id}/approve

Requires explicit human authorization. It may advance the commercial pipeline,
but must not execute payment or external communication automatically.

## POST /api/customers/{request_id}/message

External communication gate. Requires a configured authenticated connector,
valid purpose consent, and authorization.

## Financial boundary

Customer Portal APIs must never infer PAYMENT_VERIFIED or REVENUE_REALIZED from
a form submission. Those states remain owned by the Revenue Ledger and require
evidence.

## Privacy boundary

Store only data required for the stated service purpose. Marketing consent is
separate from service consent and must not be implied by submitting a request.
