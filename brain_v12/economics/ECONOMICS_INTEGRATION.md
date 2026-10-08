# Economics Integration Contract

The economics package is intentionally isolated from external side effects.

## Components
- opportunities.json: seeded opportunity registry.
- opportunity_engine.py: deterministic scoring and linear lifecycle.
- revenue_gate.py: evidence-backed confirmed-revenue constructor.
- revenue_integrity.py: evidence fingerprint and duplicate gate.
- economic_control.py: causal lifecycle, attribution, and resource budgets.
- economic_governor.py: single-path ALLOW/HOLD/STOP control.
- economic_settlement.py: deterministic settlement and ledger replay.
- economic_control_plane.py: unified facade for the above controls.
- router_bundle.py: isolated HTTP bundle for score, orchestrator, and shortlist.
- test_*.py: unit/API coverage.

## Runtime contract
The main application may mount the isolated bundle with:

    from .economics.router_bundle import router as economics_router
    app.include_router(economics_router)

This integration is intentionally documented but not claimed as mounted in app.py.

## Safety boundary
The economics subsystem does not submit applications, impersonate users, move money, or declare income without payment evidence.

Self-healing must not rewrite financial facts to repair an integrity failure.

## Revenue truth
A target, opportunity, advertised rate, expected value, or receivable is not confirmed revenue.

Confirmed revenue requires:
1. valid payment evidence,
2. unique evidence ID/fingerprint,
3. complete causal chain,
4. deterministic settlement,
5. auditable event identity.

## Verification
A deployment should run the economics test files before enabling the router in production.
