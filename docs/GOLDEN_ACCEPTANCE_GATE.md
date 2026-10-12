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
- For every non-`SIMULATED` reality level, the independent verification record must contain an Ed25519-signed attestation bound to the exact task, mission, attempt, reality level, evidence IDs, and criterion IDs.
- The verifier trust anchor is supplied out-of-band through `BRAIN_GOLDEN_VERIFIER_PUBLIC_KEY_B64`; there is no private signing key in Brain or CI.
- Signed verifier attestations expire within five minutes, require explicit mission/attempt scope, and use a persistent SQLite nonce ledger to reject replay.
- Missing evidence, mismatched reality, integrity failures, missing trust anchors, invalid signatures, expired attestations, or replayed nonces fail closed.

## Scope and limitations

The simulation harness can create synthetic verifier-labelled evidence only for `SIMULATED` smoke tests; that is a test fixture, not an independently operated verifier. Non-simulated acceptance now requires a signed statement from the trusted verifier key, but that statement alone does not prove a VM boot unless the verifier actually observes the boot and validates the executor's separate signed attestation. The gate does not execute work or provision infrastructure. Trust-anchor provisioning and verifier deployment remain operational prerequisites.

## Focused tests

```bash
python -m unittest brain_v12.tests.test_golden_acceptance_gate -v
```
