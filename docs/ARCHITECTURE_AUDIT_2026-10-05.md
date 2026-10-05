# Architecture Audit — 2026-10-05

## Status
OPEN — consolidation required.

## Canonical runtime currently indicated by the repository
- `brain_v12/` is declared by `README.md` as the current core.
- `brain_v12/app.py` instantiates `brain_v12.brain.brain_supervisor.BrainSupervisor`.
- The canonical execution contract is described as:
  Supervisor → Reusable Brain Cloud → Tests → VerificationGate → Evidence.

## Finding A-001 — Duplicate Supervisor implementations
The repository contains multiple independent `BrainSupervisor` implementations:

1. `brain_v12/brain/brain_supervisor.py`
   - Used directly by `brain_v12/app.py`.
   - Owns bounded orchestration, checkpointing, repair/retry and execution-gateway authorization.

2. `brain_v12/brain/supervisor.py`
   - Contains a second `BrainSupervisor` class with a different constructor and execution model.
   - It is still imported by `brain_v12/test_supervisor_internal_authority.py`.

3. `brain_v12/tools/brain_runtime_supervisor.py`
   - Implements a separate continuous supervisor loop over the HTTP API.
   - It is launched by `brain_v12/tools/brain_runtime_launcher.sh` and exposed through `brain_v12/tools/brain_forever.py`.

4. Legacy implementations also exist under `brain0/` and `brain6_cpp/`; these are not currently the V12 application owner but must be classified before removal.

### Classification
- `brain_v12/brain/brain_supervisor.py`: CANONICAL CANDIDATE.
- `brain_v12/brain/supervisor.py`: COMPATIBILITY / DUPLICATE — requires migration to the canonical implementation.
- `brain_v12/tools/brain_runtime_supervisor.py`: CONTINUOUS RUNTIME CONTROLLER — should become a thin launcher/adapter, not a second policy owner.
- `brain0/`, `brain6_cpp/`: LEGACY — freeze first; do not delete during this audit.

## Finding A-002 — Multiple orchestrator layers
The repository contains:
- `brain_v12/brain/orchestrator.py` — V12 cognitive orchestrator.
- `brain_v7/braincore_v2/cognitive_orchestrator.py` — legacy V7 orchestrator.
- `cloud/runtime_orchestrator.py` — cloud runtime orchestration.
- `brain/provider_hub/decision_orchestrator.py` — domain-specific commercial decision orchestration.

These should not all be treated as competing system-level leaders. Domain-specific orchestrators may remain subordinate services; V7 must be classified as legacy.

## Finding A-003 — Workflow authority is split by historical layers
The repository has both:
- `.github/workflows/brain-supervisor.yml`
- `.github/workflows/brain-github-supervisor.yml`
- `.github/workflows/brain-github-cloud.yml`
- `.github/workflows/brain-continuous-self-healing.yml`

The current contracts already distinguish runtime execution, supervisor policy, and self-healing. The next consolidation step is to explicitly document ownership and prevent duplicate policy loops.

## Immediate safe action
Do NOT delete or disable any implementation yet.

Next repair:
1. Make `brain_v12/brain/brain_supervisor.py` the sole system-level Supervisor implementation.
2. Convert `brain_v12/brain/supervisor.py` into a compatibility facade or migrate its tests/callers.
3. Keep `brain_runtime_supervisor.py` as a runtime loop that delegates policy to the canonical Supervisor.
4. Mark V7/V0/C++ supervisor/orchestrator implementations as legacy and freeze them.
5. Add an architecture invariant test preventing a second system-level Supervisor from becoming authoritative.

## Acceptance gate
Consolidation is accepted only when:
- V12 application and tests use the canonical Supervisor.
- No second Supervisor owns policy decisions.
- Continuous runtime delegates rather than duplicates policy.
- Existing functionality remains covered by tests.
- Evidence identifies the canonical owner.


## A-004 — Orchestrator ownership boundary

**Status: RESOLVED / BOUNDARY CONFIRMED**

- `brain_v12/brain/orchestrator.py` is the V12 `CognitiveOrchestrator` used by `brain_v12/app.py` and owns the V12 perceive → decide → plan → observe → learn flow.
- `brain_v7/braincore_v2/cognitive_orchestrator.py` is a legacy V7 implementation and remains frozen; it is not imported by the V12 application.
- `brain_v12/brain/autonomous_supervisor.py` is a tool-plan executor/approval gate, not the system-level Supervisor. It must not become a second system policy owner.
- The canonical system-level authority remains `brain_v12/brain/brain_supervisor.py`.
- Runtime continuity remains delegated through `brain_v12/tools/brain_runtime_supervisor.py`.

This establishes the ownership boundary without deleting legacy V7 code.
