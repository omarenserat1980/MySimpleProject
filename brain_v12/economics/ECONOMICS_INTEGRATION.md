# Economics Integration Contract

The economics package is intentionally isolated from external side effects.

## Components
- opportunities.json: seeded opportunity registry.
- opportunity_engine.py: deterministic scoring and linear lifecycle.
- revenue_gate.py: evidence-backed confirmed-revenue constructor.
- api.py: HTTP endpoints for scoring and payment verification.
- test_*.py: unit/API coverage.

## Runtime contract
The main application may mount the economics router at:
app.include_router(economics_router)

Recommended import:
from .economics.api import router as economics_router

## Safety boundary
The economics API does not submit applications, impersonate users, move money, or declare income without payment evidence.

## Verification
A deployment should run the economics test files before enabling the router in production.
