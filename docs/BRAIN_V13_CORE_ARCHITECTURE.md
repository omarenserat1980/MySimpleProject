# Brain V13 Core Architecture

This change adds the first architectural layer for the next Electronic Brain generation without replacing the existing V12 control plane.

## Canonical responsibilities

- **Reality Core**: stores observations and distinguishes FACT, BELIEF, ASSUMPTION, UNKNOWN and CONTRADICTED.
- **Mission State Machine**: gives every long-running objective a bounded lifecycle.
- **Execution Contract**: defines identity, executor, preconditions, expected results, risk and evidence requirements before execution.
- **Brain Constitution**: central non-negotiable invariants: one authoritative orchestrator, evidence before success, bounded retries and explicit approval for high-risk actions.
- **Uncertainty Engine**: prevents weak evidence from being represented as certainty.

## Control principle

The existing `BrainSupervisor` remains the single execution authority. These modules are policy/state primitives; they do not create another orchestrator or autonomous loop.

## Target lifecycle

`MISSION → UNDERSTAND → PLAN → READY → EXECUTE → OBSERVE → VERIFY → COMPLETE`

Failure path:

`VERIFY → DIAGNOSE → RECOVER → RETEST → VERIFY`

The recovery path is bounded by mission attempts and may escalate instead of retrying forever.

## Next integration stage

1. Attach Reality Core to supervisor observations.
2. Emit Execution Contracts at dispatch boundaries.
3. Persist Mission state alongside durable task state.
4. Route completion claims through the Constitution + Evidence Store.
5. Add replay/audit events.
6. Only then expose the new state in the Brain UI/API.
