# CL-000003 Deep Commercial Execution

## Purpose
Turn the customer's request into an evidence-driven execution loop that discovers real needs, builds useful digital deliverables, validates them, and pursues a real paid outcome.

## Execution modes
Brain may prepare and build:
- web applications
- websites and landing pages
- electronic/digital services
- quote and inquiry systems
- dashboards and reporting
- APIs and integrations
- promotional/product/demo videos

## Mandatory loop
DISCOVER_NEED -> QUALIFY -> DESIGN -> BUILD -> TEST -> DEMO -> CUSTOMER_ACCEPTANCE -> DELIVER -> PAYMENT_VERIFY -> RECONCILE -> REVENUE_REALIZED

## Deep execution rules
1. Research the customer's public business context and identify concrete problems worth solving.
2. Prefer one high-value, small, demonstrable solution before a large platform.
3. Reuse existing Brain and compatible open-source components.
4. Build prototypes only when they can be validated against explicit acceptance criteria.
5. Test technical behavior, usability, and delivery completeness.
6. Keep an evidence trail for requirements, builds, tests, acceptance, delivery, payment, and reconciliation.
7. Repair failed builds and tests within bounded retries.
8. Never claim customer acceptance without actual customer evidence.
9. Never claim payment from an invoice, quote, lead, traffic, test transaction, or forecast.
10. Never move money, charge a customer, sign a contract, or make an external commitment without required authorization.

## Commercial target
The target is not merely to produce code. The target is:
NEED_VALIDATED -> SOLUTION_BUILT -> CUSTOMER_ACCEPTED -> ORDER_ACCEPTED -> DELIVERED -> PAYMENT_VERIFIED -> REVENUE_REALIZED.

## Current truth
Client: CL-000003
Status: PROSPECT
Realized revenue: 0
Payment verified: false
No external customer acceptance or payment has yet been recorded.

## First execution priority
Identify the strongest immediately sellable industrial digital solution for the prospect, produce a bounded demo/prototype, prepare its offer and acceptance criteria, and stop at the authorization boundary before any external commitment.


## Autonomous execution contract

Brain should continuously evaluate the active request in bounded cycles:

1. DISCOVER — inspect the prospect's public business context and identify concrete digital opportunities.
2. PRIORITIZE — rank opportunities by customer value, buildability, evidenceability, delivery speed, and revenue potential.
3. SPECIFY — create acceptance criteria before implementation.
4. BUILD — implement the smallest useful version using existing Brain capabilities and compatible open-source components.
5. VERIFY — run technical tests, smoke tests, artifact checks, and customer-value checks.
6. DEMO — prepare a reviewable artifact without pretending it is customer-approved.
7. REQUEST_APPROVAL — stop before external commitment, pricing commitment, contract, charge, or publication that requires authorization.
8. DELIVER — only after acceptance/authorization, produce delivery evidence.
9. COLLECT — track the permitted payment path and surface blockers.
10. VERIFY_PAYMENT — require independent payment evidence.
11. RECONCILE — bind customer, order, amount, currency, delivery, and payment evidence.
12. REALIZE — only then allow REVENUE_REALIZED.

### Opportunity ranking
Prefer opportunities that:
- solve an identifiable industrial sales/operations problem;
- can be demonstrated quickly;
- can be built with existing Brain infrastructure;
- have clear acceptance criteria;
- have a straightforward lawful payment path;
- do not require Brain to move money or make unauthorized commitments.

### Failure handling
For every failed build/test:
- record the failure evidence;
- diagnose the first blocking cause;
- repair the smallest responsible component;
- rerun the relevant verification;
- do not hide or overwrite failed evidence;
- stop after bounded retries and surface the exact blocker.

### Commercial truth
A prototype is not a customer acceptance.
A customer acceptance is not payment.
Payment evidence is not sufficient for delivery recognition unless delivery/reconciliation requirements are also satisfied.
No financial state may be promoted merely because an execution cycle succeeded.
