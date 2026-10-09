# BRAIN Deep Hardware Evolution — Truth Kernel v1

## Objective

Move the Piece-First Hardware Graph from an in-memory composition model into a durable, evidence-backed hardware control plane.

The server is a projection of independent pieces and first-class connections. No physical or virtual capacity may be claimed without a provider-backed evidence chain.

## Canonical model

Mission
-> Capability Graph
-> Piece Requirements
-> Hardware Graph
-> Truth/Evidence
-> Resource Fabric
-> Capacity Gate
-> Execution Kernel
-> Backend
-> Worker
-> Telemetry
-> Reconciler
-> Recovery

## Non-negotiable invariants

1. SIMULATED, PROVISIONED, VERIFIED, ATTACHED and RUNNING are distinct truth levels.
2. RUNNING requires backend execution evidence; a boolean or caller assertion is insufficient.
3. Every capacity has one canonical owner; derived capacity cannot be counted as independent physical capacity.
4. Piece and connection reservations form one logical transaction. Partial reservation is rolled back.
5. A replacement is additive-first: discover -> verify -> connect -> reserve -> attach -> verify -> fence old -> retire old.
6. Old hardware identity is preserved when one piece is replaced.
7. Every state transition records actor, timestamp, reason, evidence IDs and fencing epoch.
8. Restart/recovery must reconstruct the graph without silently upgrading truth.
9. Stale provider observations cannot overwrite newer verified state.
10. A graph is executable only when its required subgraph, capacities, connections, health and evidence all satisfy the mission contract.

## Phase A — Durable Truth Kernel

Implement a persistence abstraction behind HardwareGraph.

Required records:
- pieces
- connections
- reservations/leases
- state transitions
- evidence references
- provider observations
- fencing epochs
- reconciliation checkpoints

The first implementation may use SQLite/local durable storage, but the interface must permit a later Postgres/cloud backend without changing graph semantics.

## Phase B — Transactional reservation

Introduce a transaction boundary spanning:
- piece reservations
- connection reservations
- Resource Fabric reservation
- lease creation
- fencing epoch update

Failure at any step must compensate every prior step.

## Phase C — Evidence-backed lifecycle

Replace boolean verification with typed EvidenceStore references.

Required transition:
DISCOVERED -> PROVISIONED -> VERIFIED -> CONNECTED -> AVAILABLE -> RESERVED -> ATTACHED -> ACTIVE

ACTIVE requires:
- backend identity
- execution ID
- observation timestamp
- provider evidence
- health evidence
- capacity reconciliation

## Phase D — Reconciliation

Build a reconciler that compares:
desired graph
vs
persisted graph
vs
provider observations
vs
backend runtime state.

Outcomes:
- MATCH
- DRIFT
- STALE
- MISSING
- UNEXPECTED
- CONFLICT
- QUARANTINE

Never auto-promote uncertain state.

## Phase E — Piece-level replacement

Make replacement a first-class transaction for:
- GPU
- RAM
- NVMe
- NIC
- CPU

Acceptance:
- unrelated piece IDs remain unchanged
- valid connection topology is rebuilt only where necessary
- old piece is fenced/quarantined
- new piece has fresh evidence
- failed replacement leaves the previous executable graph intact

## Phase F — Backend adapters

Define a common adapter contract for:
- Hyper-V
- QEMU/KVM
- Linux host
- cloud VM
- bare metal

Each adapter must expose observation and execution evidence, not merely a boolean success.

## Phase G — Execution integration

Connect GraphComposer to ExecutionKernel.

Admission must prove:
1. mission requirements
2. graph requirements
3. piece availability
4. connection compatibility
5. capacity truth
6. evidence freshness
7. lease ownership
8. fencing epoch

Only then may the backend execute.

## Phase H — Recovery

Recovery must operate at the smallest failed scope.

Examples:
GPU failure -> replace GPU subgraph
NIC failure -> replace NIC + affected network edges
NVMe failure -> replace storage piece + dependent volume path
host failure -> migrate/recompose entire affected graph

Do not rebuild healthy pieces unnecessarily.

## Single-orchestrator rule

All autonomous repair/evolution work must enter one admission queue and one Execution Kernel.

No parallel self-healing loops.
No unbounded workflow fan-out.
No recursive workflow spawning.
No continue-on-error as a substitute for a gate.

## Definition of Done

A Brain mission can request a server capability, compose it from independently managed pieces, prove every required resource with evidence, execute it through a real backend, observe it, replace one failed piece without rebuilding unrelated pieces, survive restart, reconcile drift, and recover safely.

Until these conditions are met, the system must report the server as partially virtual/provisioned rather than physically verified.
