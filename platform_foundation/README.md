# Platform Foundation

This package is intentionally independent of brain_v12.

Verified slices:

1. runtime lifecycle and health
2. in-memory state contract
3. append-only evidence ledger
4. durable SQLite state
5. explicit permission boundary
6. task state machine
7. auditable control plane

Control path:

permission -> state transition -> execute -> persist -> evidence

Unknown actions are denied by default. Irreversible actions are never implicitly authorized. A green CI workflow alone is not proof of autonomy; executable tests and evidence artifacts are required.
