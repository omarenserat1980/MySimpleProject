# BRAIN Digital Commerce

## Purpose
A dedicated commercial surface for BRAIN digital products and business services.

## Commercial state machine
PRODUCT -> ORDER_DRAFT -> PAYMENT_PENDING -> PAYMENT_VERIFIED -> DELIVERY -> REVENUE_REALIZED

An order is never revenue merely because a product is displayed, an order is created, or a payment page is opened.

## Current implementation
- `brain_v12/web/commerce.html`: public-facing digital commerce page.
- Main Brain navigation includes a direct Commerce entry.
- Product categories: AI tools, automation/software kits, intelligence packs, media toolkit.
- Business services: AI automation, software development, digital media, research/intelligence.
- Order form generates a local draft identifier only.
- No live payment provider is claimed or simulated.

## Next production integrations
1. Persistent order API.
2. Approved payment provider adapter.
3. Signed webhook verification.
4. Payment evidence and reconciliation.
5. Invoice/receipt generation.
6. Digital delivery entitlement.
7. Economic Ledger transition to `REVENUE_REALIZED` only after verification.
8. Admin/audit dashboard.
9. Refund/dispute states.
10. Revenue and conversion analytics.

## Guardrails
- Never fabricate sales, payments, customers, or revenue.
- Never store raw card data in Brain.
- Payment secrets remain server-side.
- Every financial state transition produces an audit event.
- No financial transaction is executed without explicit authorization and a configured provider.
