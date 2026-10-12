# BRAIN Human & Contract Layer Specification v1

## Purpose
Provide a Brain-owned, provider-neutral foundation for lawful interactions with real people and organizations: customers, contractors, employees, partners, suppliers, and other counterparties.

## Core principle
A person, organization, contract, payment, delivery, or legal obligation is a first-class auditable business object. ChatGPT, GitHub, a payment provider, or a workflow runner is never the owner of the commercial relationship.

## Contract lifecycle
PROSPECT → OFFERED → ACCEPTANCE_PENDING → ACCEPTED → CONTRACTED → EXECUTING → DELIVERED → ACCEPTED_BY_CUSTOMER → CLOSED

Failure/exception states include DECLINED, EXPIRED, CANCELLED, DISPUTED, BREACHED, and SUSPENDED.

## Required contract record
- contract_id
- parties and verified roles
- legal entity / contracting capacity
- scope and exclusions
- deliverables and acceptance criteria
- milestones and deadlines
- price, currency, taxes/fees where applicable
- payment terms
- responsibilities and dependencies
- evidence references
- authorization references
- jurisdiction and governing-law metadata where applicable
- version and effective dates
- audit history

## Human roles
Brain may coordinate work involving:
- customers/buyers
- employees
- independent contractors
- freelancers
- partners
- suppliers
- authorized representatives

Identity and authority must be verified to the degree required by the activity and jurisdiction.

## Permission boundary
Brain may research, draft, compare, calculate, schedule internal work, monitor evidence, and recommend actions.

Brain must not silently:
- sign a contract on behalf of a person or legal entity;
- make a personal guarantee;
- create a financial obligation;
- move funds;
- misrepresent identity, authority, licensing, registration, or tax status;
- treat an invoice as proof of payment.

External commitments require the appropriate authorization and evidence.

## Delivery and acceptance
A commercial task is not complete merely because an internal task succeeds. Delivery requires:
1. declared deliverable;
2. delivery evidence;
3. customer acceptance where contractually required;
4. reconciliation to the contract/milestone;
5. linkage to payment and revenue evidence when applicable.

## Economic linkage
Contract evidence must connect to:
OFFER → CUSTOMER → CONTRACT → DELIVERY → PAYMENT_VERIFIED → REVENUE_REALIZED → COSTS → PROFIT_VERIFIED.

Forecasts and unpaid invoices remain non-realized economic states.

## Provider independence
Human and contract records use Brain-owned schemas and exportable formats. External CRM, signature, payment, email, or marketplace services are adapters, not the source of truth.

## Audit and privacy
Material actions must be auditable. Personal data must be minimized, access-controlled, retained only as necessary, and handled according to applicable law and the company's privacy policy.

## Launch rule
Commercial operation must remain blocked until the selected legal entity, contracting authority, privacy/compliance requirements, and required human approvals are evidenced for the applicable jurisdiction and activity.
