# BRAIN HANDOFF — Piece-First Composable Hardware Fabric

Status: ACTIVE HANDOFF
Branch: brain-virtual-hardware-v2
PR: #170
Latest commit: e134f2eae81c4ac9770274481496ac6583e3460a

## Mission

Brain is receiving the current project as an engineering handoff. Treat this repository state as the baseline and continue development from the existing architecture. Do not rebuild the project from scratch.

The intended model is:

ChatGPT → Mission Control → Capability Graph → Piece Requirements → Hardware Graph → Truth/Evidence → Resource Fabric → Capacity Gate → Execution Kernel → Backend → Worker → Evidence → Verify → Recovery/Learning

A server is a projection of independent software-defined hardware-like pieces. Replacing one piece must not rebuild unrelated pieces.

## Delivered in this handoff

1. Piece-first graph model:
   - brain_v12/brain/piece_graph.py
   - first-class Piece and Connection objects
   - truth levels, capacity ownership, fencing epochs, graph reservations
2. Graph Composer:
   - brain_v12/brain/graph_composer.py
   - discovery and constraint matching
   - compose/reserve
   - independent piece replacement
   - new connection materialization for replacements
   - quarantine/fencing of old piece
   - rollback on failure
3. API:
   - brain_v12/brain/piece_graph_api.py
   - graph inspection
   - add piece
   - add connection
   - compose
   - replace
   - failure/reconciliation
4. app.py integration.
5. Tests:
   - test_piece_graph.py
   - test_graph_composer.py
   - both added to brain-fabric-tests.yml

## Non-negotiable truth rules

- Never claim physical CPU/RAM/GPU/storage/network capacity without provider evidence.
- SIMULATED, OBSERVED, VERIFIED and ATTESTED are different truth levels.
- A logical federation is not unified physical memory.
- A reservation is not proof that a backend actually attached a resource.
- RUNNING requires backend/runtime evidence, not a boolean flag.
- Do not double-count derived/virtual capacity.
- Do not silently reuse an old connection endpoint when replacing a piece.

## Current known weaknesses to solve next

P0:
- Make graph reservations transactionally coupled to ResourceFabric.
- Replace in-memory graph state with durable state.
- Require EvidenceStore/backend evidence for graph activation.
- Couple graph activation to ExecutionKernel admission/fencing.

P1:
- Add real GraphComposer constraint solving for topology, NUMA, PCIe lanes, power, cooling, storage buses and network paths.
- Make connection capacity independently reservable/accountable.
- Add reconciliation against provider state and stale-provider fencing.
- Add typed dependency/failure propagation.
- Add graph identity/versioning and audit events.
- Add compensation/recovery after partial backend failures.
- Prevent concurrent replace/compose races with atomic persistence/locking.

P2:
- Backend adapters: Hyper-V, QEMU/KVM, container, cloud VM/service, bare metal.
- Hardware discovery adapters and evidence collectors.
- Piece-level health/telemetry with bounded retention.
- Cost/limits/fallback policy per piece.
- Optimization: least disruption, highest evidence confidence, lowest cost, best locality.

## Required next engineering loop

SCAN → REVIEW → PLAN → IMPLEMENT → TEST → EVIDENCE → VERIFY → ACCEPT/REJECT → LEARN

Every accepted change must leave inspectable evidence.

## First Brain tasks

1. Audit graph_composer.py for correctness, especially replacement connection orientation and rollback.
2. Run the focused piece graph tests and full Brain Fabric gate.
3. Fix every failure found; do not hide failures with continue-on-error.
4. Implement durable graph persistence.
5. Implement atomic Piece + Connection + ResourceFabric reservation.
6. Replace boolean activation verification with EvidenceStore-backed verification.
7. Add ExecutionKernel admission for graph activation.
8. Report exact evidence: commit SHA, tests, failures, and remaining blockers.

## Collaboration contract

ChatGPT is handing architecture and current implementation state to Brain.
Brain should critique the implementation rather than blindly accept it.
If Brain finds a design flaw, record:
- finding
- severity
- evidence
- proposed correction
- test proving the correction

Do not merge speculative code. Do not report success without test evidence.

## Definition of done for the next milestone

A command such as "replace GPU-01 with an available compatible GPU" must result in:

discover → verify candidate → plan connections → reserve piece+connections+resource capacity → fence old piece → detach → attach replacement → backend verify → activate → emit evidence

If any stage fails:
rollback/compensate → preserve graph integrity → emit failure evidence.

This document is the authoritative handoff for the Piece-First phase.
