# India Open-Source Revenue Stack

## Purpose

Use Indian/open-source business software as external, license-respecting building blocks for Brain's commercial workflow. Do not copy GPL source into Brain's proprietary codebase unless the project's licensing obligations are intentionally accepted.

## Candidate 1 — ERPNext / Frappe

- Repository: https://github.com/frappe/erpnext
- License: GPL-3.0
- Relevant capabilities: accounting, CRM, sales orders, delivery/fulfillment, projects, manufacturing and reporting.
- Integration rule: prefer API/service boundary or a separately licensed deployment. Do not copy GPL implementation files into Brain without an explicit license decision.
- Commercial use: can support quote/order/delivery/accounting evidence collection, but its records are not automatically accepted as Brain revenue evidence. Payment still requires independent verification.

## Candidate 2 — Frappe Framework

- Repository: https://github.com/frappe/frappe
- License: MIT
- Relevant capabilities: Python/JavaScript web framework, database-backed applications, REST APIs and webhooks.
- Integration rule: suitable for an adapter/service boundary where technically useful.
- Commercial use: useful for building customer-facing operational tooling; it does not by itself prove payment.

## Candidate 3 — Frappe CRM

- Repository: https://github.com/frappe/crm
- License: AGPL-3.0
- Relevant capabilities: open-source CRM and sales workflow.
- Integration rule: keep as a separately deployed service or isolate the integration behind APIs unless AGPL obligations are intentionally accepted.
- Commercial use: prospect, opportunity and customer workflow evidence only; leads/opportunities are never revenue.

## Candidate 4 — India-specific payroll extension

- Repository: https://github.com/frappe/india-payroll
- License: GPL-3.0
- Relevant capabilities: India-specific payroll/tax workflows.
- Integration rule: not a revenue proof source for Brain; use only where Indian payroll/compliance is actually relevant.

## Revenue hard gate

PROSPECT -> OFFER_PREPARED -> CUSTOMER_VALIDATED -> ORDER_ACCEPTED -> DELIVERY_VERIFIED -> PAYMENT_VERIFIED -> REVENUE_REALIZED -> PROFIT_VERIFIED

REVENUE_REALIZED requires independently verified payment evidence bound to the customer/order/amount/currency plus delivery evidence. CI success, ERP records, invoices, forecasts, leads, clicks, or generated test fixtures cannot substitute for payment evidence.

## No fabricated proof

- TEST fixtures remain test fixtures.
- No automatic contract, charge, purchase, withdrawal, or transfer.
- No revenue claim without independent payment evidence.
- No profit claim without attributable cost evidence and reconciliation.
