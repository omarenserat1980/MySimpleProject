# Unified Path Engine V1

Path Engine is the shared orchestration boundary for Brain paths. It keeps the
execution model uniform while allowing each domain to supply its own executor.

## Contract

`PathSpec` defines a goal, ordered steps, and safety budgets.

Every run passes through:

`authorization -> policy -> execute -> verify -> evidence -> next step`

Terminal states are:

- `SUCCEEDED`
- `FAILED`
- `BLOCKED`
- `STOPPED`

## Safety rules

1. Only one active run is allowed for the same goal.
2. Every run has an explicit attempt budget.
3. Missing executor, denied gates, and verification failures cannot silently continue.
4. Each execution and gate decision produces evidence.
5. The engine is synchronous in V1; it does not create child repair loops or parallel
   workers.

## Integration order

1. Keep the engine dependency-free and independently tested.
2. Add a thin adapter in the central Brain orchestrator.
3. Route diagnosis/self-healing first.
4. Route Android/Termux and Windows execution through the same contract.
5. Add media/publishing paths after runtime paths are stable.
6. Feed successful evidence into Path Evolution so proven paths can be preferred.

V1 intentionally does not replace existing paths in-place; it establishes the
common contract before migration.
