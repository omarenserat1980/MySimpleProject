# BRAIN STANDING AUTHORIZATION & CUSTOMER CONSENT POLICY

## Purpose

The operator may give BRAIN a standing delegation for routine decisions so the system does not repeatedly ask for approval. This delegation is bounded, auditable, revocable, and never treated as unlimited authority.

## Standing operator authorization

The standing authorization means:

> BRAIN may select and execute the objectively preferable routine option when it is within an approved policy, does not create personal legal/financial liability, does not make an irreversible high-impact commitment, and does not exceed configured commercial or privacy limits.

The phrase "best for me" is operationalized as **best under the Brain decision policy**, not as unrestricted discretion. The decision engine must record the criteria, alternatives considered, evidence, policy version, confidence, and reason.

## Actions covered by default

BRAIN may execute without asking the operator again when all gates pass:

- routine workflow routing and scheduling;
- ordinary customer-service responses using approved templates;
- drafting and sending routine operational messages when the customer has already consented to that communication channel and the message contains no new legal/financial commitment;
- routine quotations within an approved price floor/range and approved scope;
- ordinary production/delivery actions already accepted by the customer;
- reminders, status updates, follow-ups, and non-binding scheduling changes;
- reversible technical remediation and retries;
- selecting among equivalent approved providers/workers according to cost, reliability, quality, and policy.

## Mandatory operator approval

The standing authorization does NOT cover:

- signing or accepting a contract on the operator's personal behalf;
- personal guarantees, borrowing, debt, commingling, or undocumented personal payments;
- transactions above a configured monetary threshold;
- changing the price floor or commercial policy;
- refunds, credits, chargebacks, or financial settlements outside pre-approved rules;
- legal admissions, waivers, settlements, regulatory representations, or litigation decisions;
- changing ownership, beneficial-owner, tax, licensing, or registration information;
- disclosure of sensitive personal/customer data outside approved purposes;
- irreversible deletion of authoritative records;
- public statements that create a new legal/commercial commitment;
- actions specifically marked HUMAN_APPROVAL_REQUIRED by policy.

## Customer consent is separate

The operator's standing authorization never substitutes for customer consent.

Customer approval must be explicit and scoped to the relevant proposal, quote, service, deliverable, payment terms, communication permission, or data-processing purpose. A customer's silence, continued conversation, or receipt of a message is not treated as acceptance unless an applicable documented agreement explicitly makes it so.

BRAIN may execute immediately after a customer approval is captured and validated against the exact scope, version, price/currency, deadline, and terms approved.

## Two-layer decision gate

1. **Operator authority gate:** Is BRAIN authorized to act without asking the operator?
2. **Customer consent gate:** Has the customer approved the exact action where approval is required?

Both gates must pass before execution.

## Evidence

Every autonomous decision must record:

- decision ID;
- actor = BRAIN;
- authority basis and policy version;
- action and scope;
- customer/account/case reference where applicable;
- alternatives considered;
- evidence references;
- risk classification;
- timestamp;
- resulting execution/evidence reference.

## Revocation

A standing authorization can be revoked at any time. The system must stop new autonomous actions covered by the revoked authority while preserving already-created audit evidence.

## Default on uncertainty

If the policy, authority, customer consent, identity, price, scope, or evidence is ambiguous, BRAIN must pause and route to the appropriate approval gate rather than infer consent.
