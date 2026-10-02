# Brain Customer Operations & Trust Layer

## Purpose

This layer unifies customer handling across discovery, communication, offers,
delivery, payment evidence and after-sales support without turning the Brain
into an autonomous financial or messaging actor.

## Operating principles

1. Evidence before claims.
2. Consent before marketing communication.
3. Minimum necessary customer data.
4. Customer decisions remain human decisions.
5. External communication is gated.
6. Financial execution is disabled by default.
7. Payment status changes only from verifiable evidence.
8. Contracts, invoices, refunds and payments require explicit authorization.
9. Audit every material state transition.
10. Never fabricate customer identity, payment, revenue or testimonials.

## Customer lifecycle

PROSPECT -> DISCOVERED -> QUALIFIED -> NEEDS_ANALYZED -> OFFER_READY ->
HUMAN_APPROVAL -> CUSTOMER_ACCEPTED -> CONTRACTED -> DELIVERING -> DELIVERED ->
INVOICE_ISSUED -> PAYMENT_PENDING -> PAYMENT_VERIFIED -> REVENUE_REALIZED ->
AFTER_SALES -> CLOSED

## Communication channels

Current product channel:
- BRAIN_PORTAL: Browser-first Brain Cloud UI.

Connector-ready channels:
- EMAIL
- WHATSAPP
- TELEGRAM
- SOCIAL

A channel is not considered active merely because its name exists in code.
Activation requires a real connector, authentication, permission, test evidence
and an audit record.

## Financial boundary

The Brain may calculate expected prices, costs, margins and payment states.
It must not claim that money moved, execute a transfer, issue a refund, or mark
revenue realized without the required evidence and authorization.

## Evidence states

EXPECTED -> READY_FOR_REVIEW -> AUTHORIZED -> EXECUTED -> VERIFIED

VERIFIED is reserved for evidence-backed outcomes. A workflow being green is
not itself proof that a customer interaction or payment occurred.

## Regulatory adapter boundary

Legal, consumer-protection, privacy, advertising and financial rules can vary
by jurisdiction and over time. Jurisdiction-specific rules must therefore be
implemented as versioned policy adapters and checked before external execution.
This document is an engineering policy, not legal advice.
