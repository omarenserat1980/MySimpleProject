# Brain Recovery Architecture

## Golden baseline
- Checkpoint: BRAIN-GOLDEN-01
- Main commit: 343280f2884079655f33f2264f27f5c283cf74b0
- Repository: omarenserat1980/MySimpleProject
- Golden checkpoint branch: checkpoint/brain-golden-01-2026-10-08
- Recovery implementation: PR #155

## Source of truth
1. GitHub source is canonical for Brain code and workflows.
2. Runtime devices are executors, not the source of truth.
3. Runtime state is backed up separately from source.
4. Secrets are referenced by location/name only and never committed.

## Recovery layers
- Source: exact Git commit, tests, workflows and documentation.
- State: SQLite memory/state, evidence database, durable sync queue and runtime evidence.
- Device: Android/Termux and Windows executors are replaceable.
- Verification: restore is complete only after integrity and Brain verification gates pass.

## Target recovery
new device -> bootstrap -> verify source -> restore state -> register executor -> replay sync -> verify evidence -> READY

## Rule
The phone must never be the only copy of important Brain state.
