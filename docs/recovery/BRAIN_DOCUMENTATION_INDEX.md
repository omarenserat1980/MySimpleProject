# Brain Documentation Index

This directory is durable operational documentation for Brain.

## Recovery
- BRAIN_RECOVERY_ARCHITECTURE.md — source/state/device recovery.
- BRAIN_TERMUX_OPERATIONS.md — Termux paths, scripts and runtime contract.
- DESKTOP_COMMANDER_CONFIGURATION.md — current Desktop Commander profile and execution boundary.

## Canonical references
- recovery/BRAIN_GOLDEN_CHECKPOINT_01.json
- BRAIN-GOLDEN-01
- .github/workflows/brain-golden-recovery.yml
- PR #155

## Documentation rule
Every material Brain change should document:
1. What changed.
2. Why.
3. Source commit/branch.
4. Runtime paths.
5. Environment variable names.
6. Device/executor role.
7. State locations.
8. Recovery implications.
9. Verification evidence.
10. Secrets by reference only, never by value.

## Immutable checkpoint rule
Golden checkpoints are restoration anchors. Future work uses new branches and does not rewrite the historical checkpoint definition.

## Source versus state
Git stores source and documentation. Runtime databases, evidence and durable queues are separate state and must be captured by an approved recovery mechanism.
