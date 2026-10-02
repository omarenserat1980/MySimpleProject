# Brain Marketing Engine

The Marketing Engine is the governed execution layer for Electronic Brain marketing.

## Lifecycle

DRAFT -> REVIEW -> APPROVED -> SCHEDULED -> PUBLISHED -> MEASURED

Rejected and cancelled campaigns cannot continue.

## Safety and evidence

- External publication requires APPROVED state.
- Paid promotion requires explicit authorization outside this engine.
- Campaign events and approvals are retained as an audit trail.
- Metrics are recorded only after publication.
- No fabricated testimonials, customer counts, revenue claims, or performance results.

## Integration target

Connect this engine to:
- Brain CRM / leads
- content repository
- analytics
- social publishing adapters
- website lead forms
- approval UI
- audit/event store

The current implementation is intentionally an in-memory reference implementation. Persistence and external adapters must be added as separate layers so the core lifecycle remains testable and provider-independent.
