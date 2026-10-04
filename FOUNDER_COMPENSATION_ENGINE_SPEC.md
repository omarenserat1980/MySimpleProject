# Founder Compensation Engine

## Purpose

Define a Brain-owned, evidence-first policy for founder compensation that can target an exceptionally high global compensation level without confusing forecasts, company revenue, profit, equity value, or cash available for payment.

The objective is not to promise a fixed salary today. The objective is to make exceptional founder compensation a measurable consequence of exceptional, verified company performance.

## Core principles

1. Verified money only — compensation eligibility is based on independently evidenced cash/revenue/profit, never forecasts, pipeline value, invoices alone, or simulated balances.
2. Company first — compensation must preserve payroll, taxes, customer obligations, critical infrastructure, security, recovery, and reinvestment requirements.
3. No hidden ownership evasion — public privacy may be designed lawfully, but Brain must never conceal beneficial ownership or compensation from authorities, banks, auditors, courts, or other legally required disclosures.
4. Separate accounting concepts — founder salary, bonus, dividend/distribution, reimbursement, company expense, revenue, and profit are distinct ledger concepts.
5. No automatic external transfer — the engine may calculate eligibility and prepare an auditable recommendation; actual payment requires the applicable human/legal/accounting authorization and payment controls.
6. Jurisdiction-aware — tax, employment, corporate, securities, and director-compensation rules must be versioned by jurisdiction and reviewed by qualified professionals before execution.
7. Long-term alignment — very large founder wealth should preferentially come from lawful equity/long-term incentive structures when appropriate, rather than draining operating cash through an unsustainable salary.
8. No negative-surprise autonomy — a compensation recommendation must never silently create a debt, personal guarantee, tax obligation, or external financial side effect.

## Compensation architecture

Brain tracks four separate channels:

- FOUNDER_BASE_COMPENSATION: recurring salary/director compensation where legally applicable.
- FOUNDER_PERFORMANCE_COMPENSATION: bonus tied to verified performance.
- FOUNDER_EQUITY_VALUE: ownership/long-term incentive value; not treated as cash revenue.
- FOUNDER_REIMBURSEMENT: documented business expenses paid back to the founder; not salary or profit.

Optional distributions/dividends are tracked separately from salary and only when legally and financially permitted.

## Eligibility gates

A founder compensation recommendation may advance only when:

PAYMENT_VERIFIED -> REVENUE_REALIZED -> COSTS_VERIFIED -> PROFIT_VERIFIED -> RESERVE_GATE -> COMPENSATION_ELIGIBLE

The engine must block when any required evidence is missing, stale, disputed, reversed, refunded, or unreconciled.

### Reserve gate

Before recommending extraordinary compensation, Brain must reserve sufficient funds for:

- taxes and statutory obligations;
- payroll and contractor commitments;
- customer refunds/chargebacks and contractual liabilities;
- infrastructure and security;
- recovery/backup requirements;
- committed operating costs;
- a board/owner-approved operating reserve;
- documented reinvestment requirements.

## Global-compensation ambition

The system may maintain a target such as GLOBAL_TOP_TIER_FOUNDER_COMPENSATION.

This is an ambition/benchmark class, not a guaranteed payment amount.

The engine should compare proposed total annual compensation against current market benchmarks using dated, source-backed evidence. It must not manufacture a benchmark or claim that Brain is among the world's highest-paid companies without evidence.

## Safety formula

A simplified maximum-cash recommendation is:

available_for_founder_cash = verified_free_cash - protected_reserves - committed_liabilities - approved_reinvestment

Then:

recommended_cash_compensation <= available_for_founder_cash * approved_founder_share_limit

The actual share limit is policy/configuration and must be approved; it must never be inferred from an arbitrary desire for a large salary.

## Evidence record

Every compensation decision should contain:

- compensation_id
- founder_id / legal payee reference
- compensation_type
- period
- proposed_amount
- currency
- verified_revenue_refs
- verified_cost_refs
- verified_profit_refs
- reserve_evidence_ref
- benchmark_evidence_ref
- jurisdiction_policy_ref
- approval_ref
- calculation_version
- created_at
- status
- audit_event_refs

## Required states

PROPOSED -> EVIDENCE_CHECKED -> RESERVE_CHECKED -> APPROVAL_PENDING -> APPROVED -> PAYMENT_AUTHORIZED -> PAYMENT_VERIFIED

Failure/exception states:

BLOCKED, REJECTED, CANCELLED, REVERSED, DISPUTED.

APPROVED does not mean money moved. PAYMENT_VERIFIED requires independent payment evidence.

## Anti-fake-success rules

The engine must reject:

- forecasted revenue as earned revenue;
- unpaid invoices as payment proof;
- customer-uploaded receipts as sole independent payment proof;
- paper profit without verified reconciliation;
- equity valuation as cash available for salary;
- circular transfers between founder and company as revenue;
- undisclosed related-party transactions;
- compensation that would breach protected reserves;
- claims of tax/legal compliance without evidence.

## Autonomy boundary

Brain may autonomously:

- calculate compensation scenarios;
- benchmark compensation;
- identify whether evidence gates are satisfied;
- prepare a recommendation;
- create an audit record;
- forecast the effect of different compensation levels.

Brain must require the applicable authorization before:

- signing a compensation agreement;
- creating a legally binding obligation;
- initiating an external payment;
- changing tax/legal filings;
- moving company funds;
- representing a compensation amount as legally approved.

## Success definition

The founder's desired outcome is:

EXCEPTIONALLY HIGH, SUSTAINABLE, LAWFUL, EVIDENCE-BACKED COMPENSATION generated by a highly profitable Brain company.

The company must become capable of paying the compensation before Brain represents it as earned or payable.
