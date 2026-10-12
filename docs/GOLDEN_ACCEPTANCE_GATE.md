# Golden Acceptance Gate

The `GoldenAcceptanceGate` is a verification layer, not a second task orchestrator. It reuses `EvidenceStore` and requires a complete, attempt-scoped evidence bundle before returning `GOLDEN_LOOP_VERIFIED`. Every `BrainSupervisor.transition(..., phase="deliver", status="completed")` call now requires explicit golden acceptance criteria; direct legacy delivery calls without the contract are blocked and recorded. The `deliver_if_golden(...)` helper delegates to that same guarded transition path.

## Acceptance requirements

- Every declared criterion maps to a required runtime evidence kind.
- Evidence is filtered by task, mission, and attempt.
- Each evidence payload must pass the existing SHA-256 integrity check.
- CI-only evidence cannot satisfy a runtime criterion.
- Runtime evidence must declare the exact expected reality level.
- A separate `independent_verification` record must reference all selected evidence IDs and all criterion IDs.
- The independent verifier's producer must differ from the producers of the accepted runtime evidence.
- Missing evidence, mismatched reality, integrity failures, or missing independent verification fail closed.

## Scope and limitations

The simulation harness can create synthetic verifier-labelled evidence only for `SIMULATED` smoke tests; that is a test fixture, not an independently operated verifier. This gate does not execute work, create executor attestations, prove a VM boot, or establish a remote identity. `REMOTE_EXECUTION_VERIFIED` is only a requested reality label here; callers must ensure the underlying evidence was produced by an actually authorized and attested backend. The gate's result is only as trustworthy as the evidence producers and authorization path.

## Focused tests

```bash
python -m unittest brain_v12.tests.test_golden_acceptance_gate -v
```
