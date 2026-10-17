# BRAIN AI — First Commercial Offer and Revenue Evidence Gate

Status: DRAFT FOR OWNER REVIEW — NO CUSTOMER OR REVENUE CLAIMS

## Purpose

Give the project a practical first commercial path that does not depend on ASIC fabrication, paid cloud, or fictitious income. This is an internal specification, not a public offer or legal contract.

## Candidate first offer

**Software Reliability Diagnostic Report**

Deliverable:
- Review a customer-provided software repository or test log.
- Identify reproducible failures and risks.
- Provide a prioritized report with evidence, reproduction steps, and suggested fixes.
- If authorized and technically feasible, provide a patch on a separate branch for customer review.

Boundaries:
- No promise of zero bugs, guaranteed uptime, guaranteed business outcomes, or guaranteed revenue.
- No access to customer secrets unless strictly necessary and explicitly authorized; never request passwords or private keys.
- No production changes without explicit customer approval.
- Do not publish customer code or findings without permission.
- Work only within the agreed scope and available tools.

## Before selling

1. Create one sanitized demonstration using a toy project or the user's own public repository, and disclose the exact scope.
2. Define what inputs the customer supplies and what files they receive.
3. Determine an honest price only after estimating time, support, fees, taxes and applicable obligations. Do not invent a price or claim market validation.
4. Prepare a plain-language scope, delivery date, revision limit, privacy statement and refund/cancellation terms.
5. Confirm the owner's legal ability to provide the service and invoice in Jordan before accepting a paid engagement.
6. Verify payment-provider eligibility for the actual legal status. Do not treat sandbox transactions as customer revenue.

## Evidence record schema

For each prospective engagement, store only non-sensitive identifiers and evidence references:
- offer_id
- lead_status
- customer_authorization_reference
- agreed_scope_version
- quote_reference
- payment_status and payment_evidence_reference
- delivery_artifact_hash
- customer_acceptance_reference
- direct_costs
- refunds_or_disputes
- net_result
- evidence_review_status

Never store card data, passwords, tokens, bank credentials, private keys or unnecessary personal data in this repository. Keep customer identity records in an appropriate private system.

## Revenue status definitions

- NOT_STARTED: no customer opportunity.
- LEAD_ONLY: potential customer, no accepted scope.
- QUOTED: proposal issued, not accepted.
- ACCEPTED_UNPAID: scope accepted, payment not verified.
- PAID_UNDELIVERED: authentic payment verified, delivery pending.
- DELIVERED_AWAITING_ACCEPTANCE: delivery evidence exists, acceptance pending.
- COMPLETED: payment and delivery/acceptance are evidenced.
- REFUNDED_OR_DISPUTED: refunded or disputed; exclude from net realized revenue until reconciled.

A test/sandbox payment is never a live customer payment. Revenue, payout, and profit must not be inferred from a quote, estimate, transaction ID alone, or simulated record.

## Zero-budget restriction

No ads, paid domains, subscriptions, cloud services, payment-provider activation fees, or registration fees are authorized. Begin with free documentation and a demonstrable deliverable; pause before any action that incurs a cost.
