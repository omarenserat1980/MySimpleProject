# BRAIN Commercial Governance Specification v1

## Purpose
This specification governs how Electronic Brain prices, quotes, contracts, invoices, accepts payments, promotes products, and records revenue. It is an execution policy, not a substitute for jurisdiction-specific legal or tax advice.

## Core invariants
1. A price must be explainable from recorded cost, market/value evidence, applicable tax/fees, risk, and approved margin policy.
2. A quote is not a contract until the required customer acceptance is recorded.
3. An invoice is not proof of payment.
4. PAYMENT_PENDING cannot become PAYMENT_VERIFIED without independent payment evidence.
5. PAYMENT_VERIFIED cannot become REVENUE_REALIZED without the Revenue Ledger rules.
6. Service consent, marketing consent, and analytics consent are separate purposes.
7. Promotions must have an owner, eligibility, period, reference price, promotional price/rule, and audit evidence.
8. Agents may recommend; they may not bypass approval, tax, payment-verification, or legal gates.
9. Every material commercial decision is auditable.
10. Rules are versioned by jurisdiction and effective date.

## Lifecycle
PRODUCT → PRICED → QUOTED → CUSTOMER_ACCEPTED → CONTRACTED → INVOICED → PAYMENT_PENDING → PAYMENT_VERIFIED → DELIVERED → REVENUE_REALIZED

Alternative exits: CANCELLED, REFUNDED, DISPUTED, FAILED.

## Jurisdiction rule record
Each legal/tax/payment rule should carry:
- RULE_ID
- JURISDICTION
- SOURCE_TITLE
- SOURCE_URL
- VERSION
- EFFECTIVE_FROM
- EFFECTIVE_TO (nullable)
- APPLIES_WHEN
- REQUIRED_ACTION
- EVIDENCE_REQUIRED
- APPROVAL_REQUIRED

## Pricing decision
PRICE_FLOOR = direct_cost + allocated_operating_cost + payment_cost + risk_reserve + applicable mandatory costs.
TARGET_PRICE additionally considers market evidence, customer value, scope, service level, and approved margin policy.
No below-floor sale without explicit human approval and an audit record.

## Quote/contract
Quotes must identify product/service, scope, quantity, currency, price, taxes/fees where applicable, validity period, delivery, payment terms, cancellation/refund terms, IP/licensing terms, and applicable jurisdiction/terms. Required acceptance/signature evidence must be retained.

## Payment
Supported methods are provider adapters, not hard-coded assumptions: card, bank transfer, wallet, payment gateway, and other approved methods. Store provider transaction identifiers and verification evidence; never store card PAN/CVV in Brain.

## Invoice/tax
Invoice generation must consult the jurisdiction/tax rule set. The system must distinguish subtotal, discounts, taxes, fees, and total due. Where electronic invoicing is mandatory, route through the applicable approved/connected e-invoicing path.

## Promotion
A promotion must specify campaign ID, product, reference price basis, promotional rule, dates, eligibility, consent basis, approval, and evidence. Marketing communication is not implied by service consent.

## Audit
Every state transition records actor/agent, timestamp, policy version, evidence references, prior state, new state, and approval where required.

## Non-goals
This specification does not declare a transaction legally compliant merely because a rule record exists. Final legal, tax, licensing, consumer-protection, payment-regulation, and cross-border determinations remain jurisdiction- and transaction-specific.
