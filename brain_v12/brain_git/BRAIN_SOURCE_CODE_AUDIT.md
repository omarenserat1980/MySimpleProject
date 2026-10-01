# BRAIN SOURCE CODE ARCHITECTURE AUDIT

Date: 2026-10-01
Authority: BRAIN_GIT_PRIMARY
Scope: brain_v12/ supervisor, device bridge, Brain Git, workflow engine, cinema completion gate, API boundaries, and open-source architectural benchmarks.

## Executive result

Brain has a strong architectural direction: explicit orchestration phases, evidence-based verification, device-agnostic execution, a Brain-owned Git boundary, audit records, and a cinema completion gate. The main weakness is not the ideas; it is that several production guarantees are currently represented as lightweight Python files rather than durable, transactional platform guarantees.

No claim is made that every open-source repository in the world was exhaustively inspected. The study uses representative mature open-source systems and their published architecture/source documentation as design benchmarks, including Forgejo, GitLab Runner, Temporal, and Argo Workflows.

## Strengths to preserve

1. Supervisor contract: Discover -> Plan -> Select Backend -> Execute -> Verify -> Repair -> Retry -> Deliver.
2. Bounded retries and explicit repair actions rather than unbounded self-healing.
3. Device identity is dynamic; execution should be capability-driven.
4. Brain Git separates internal authority from optional GitHub mirroring.
5. Cinema completion is evidence-based rather than equating workflow success with film success.
6. Audit records exist for Brain Git operations.
7. Git object correctness is delegated to the standard Git implementation instead of reimplementing Git internals.

## Critical weaknesses found

### W1 Durable workflow state is too weak
BrainWorkflowEngine writes one JSON file before/after subprocess execution. A process crash can leave QUEUED/RUNNING state stale and there is no lease, heartbeat, recovery worker, event history, idempotency key, cancellation protocol, or durable retry policy.

### W2 Supervisor simulation can produce false confidence
run_simulation() marks a failed simulated verification as completed_after_repair without actually re-running a real verifier. Simulation must never be used as production evidence.

### W3 Completion Gate is necessary but currently insufficient
It checks final.mp4, manifest, marker, ffprobe, audio/video, duration > 1, and manifest status. It does not yet enforce the cinema contract of 7200 seconds ± tolerance, 1000x650, independent decode smoke, master-QC evidence, per-part/shard evidence, artifact hash, or consistency between manifest and actual file.

### W4 Brain Git is metadata/API ownership, not yet a complete Git hosting platform
The current service uses local bare Git repositories and SQLite metadata. clone_url() points to an HTTP URL but no Git smart HTTP protocol endpoint is implemented. Authentication/RBAC, repository permissions, pull requests, issues, hooks, packages, object/artifact storage, quotas, backup/restore and HTTP push/fetch are not yet complete.

### W5 Queue/executor separation is incomplete
The workflow engine launches subprocesses directly. A mature runner model separates scheduler/queue from executors and lets multiple heterogeneous executors pull work. GitLab Runner and Forgejo use this separation.

### W6 API security is incomplete
Brain Git routes shown in the current API have no authentication/RBAC layer. Sensitive repository mutation and workflow execution must not be reachable as unauthenticated operations in production.

### W7 Tests are too narrow
Current tests cover small repository and workflow smoke paths. They do not test crash recovery, concurrent claims, stale leases, authorization, path traversal, command injection, idempotency, cancellation, retry backoff, artifact corruption, or end-to-end cinema verification.

### W8 Audit is not a tamper-evident event chain
Each audit row stores a SHA-256 digest of that row, but there is no previous-digest chain, signed checkpoint, actor identity, authorization decision, or append-only storage policy. A hash of a mutable row is not itself tamper evidence.

## Open-source patterns to adopt

### Temporal -> durable execution
Temporal documents durable execution, event history, task queues, retries, timeouts, heartbeats and replay/recovery. Brain should adopt the underlying patterns without requiring Temporal itself: durable event history, deterministic workflow state, activity/task separation, retry policies, heartbeat leases, idempotency, cancellation and recovery.

### Argo Workflows -> explicit retry policy
Argo supports retry limits, retry policies, conditional expressions and exponential backoff. Brain should replace generic retry_backend with typed failure classes plus policy: transient infrastructure, executor failure, deterministic code failure, invalid artifact, authorization failure, and permanent policy failure.

### Forgejo -> Git service boundary
Forgejo separates repository/Git handling, models, services, routers and tests, and leaves Git object manipulation to the git binary. Brain should preserve this separation while adding its own authority, policy and audit layer.

### Forgejo Actions -> server/runner split
Forgejo uses a server that hands out workflow runs and runners that execute them; runners are selected from pools. Brain should implement the same conceptual boundary: Brain Scheduler -> Task Queue -> Capability Matching -> Agent/Executor -> Result/Evidence.

### GitLab Runner -> executor interface
GitLab Runner explicitly separates dispatching jobs from executor implementations. Brain should define a stable Executor interface and implement Termux, local process, container, remote host, and future GPU/Android executors behind it.

## Target Brain architecture

Control Plane
  -> Durable Event Store
  -> Scheduler / Task Queue
  -> Capability Registry
  -> Policy + Authorization
  -> Executor Adapter
  -> Evidence Store
  -> Verification Engine
  -> Repair Planner
  -> Artifact Store
  -> Audit Chain
  -> UI/API

Workflow lifecycle:
SUBMITTED -> PLANNED -> QUEUED -> CLAIMED -> RUNNING -> VERIFYING ->
  VERIFIED -> DELIVERED
or
  FAILED -> CLASSIFIED -> REPAIRING -> RETRY_QUEUED
or
  BLOCKED

Every state transition must have an event, actor, timestamp, attempt number and idempotency key.

## Cinema-specific contract

A film cannot be declared complete from process exit code alone.
Required evidence:
- final.mp4 exists
- exact expected target duration (7200s for the two-hour production) within explicit tolerance
- 1000x650 video geometry
- video stream present
- audio stream present
- independent ffmpeg decode smoke passes
- manifest parses
- manifest status is VERIFIED_COMPLETED
- manifest/master QC agrees with ffprobe
- all required parts/shards have evidence
- final artifact SHA-256 recorded
- completion_gate.json records the complete evidence set

## Implementation order

P0 — Reliability foundation
1. Durable event log + atomic state transitions.
2. Task queue with lease/heartbeat/stale-task recovery.
3. Idempotency keys and attempt IDs.
4. Typed failure classification and exponential backoff.
5. Authentication/RBAC before exposing mutation APIs.

P1 — Verification foundation
6. Upgrade FilmCompletionGate to the full cinema contract.
7. Independent decode test.
8. Evidence bundle + artifact hashes.
9. Verification must be a separate step/process from rendering.

P2 — Brain Git
10. Implement real Git smart HTTP/SSH service boundary or integrate a proven self-hosted Git server behind Brain policy.
11. Repository permissions, audit actor, PR/merge model, hooks, backup/restore.
12. Keep GitHub as optional mirror only.

P3 — Execution federation
13. Capability registry.
14. Executor interface.
15. Termux/local/container/remote adapters.
16. Scheduler selects executor by capabilities, availability and policy rather than fixed device identity.

P4 — Independence Gate
17. Disable GitHub credentials and network dependency in a test environment.
18. Create/commit/branch/clone workflow through Brain Git only.
19. Execute a workflow through Brain Scheduler only.
20. Produce and verify an artifact through Brain only.
21. Reboot/restart the Brain service and prove recovery from durable state.
22. Only then mark GitHub external dependency as OPTIONAL.

## Non-negotiable engineering rules

- Never convert a simulated result into production evidence.
- Never declare film completion from workflow SUCCESS alone.
- Never allow an unauthenticated mutation endpoint in production.
- Never bind a task permanently to one device before capability selection.
- Never retry permanent failures indefinitely.
- Never store secrets in repository source.
- Every repair must produce new evidence.
- Every successful delivery must point to verifiable artifact evidence.

## Benchmark sources

- Temporal durable execution and event history: https://github.com/temporalio/documentation
- Argo Workflows retry strategies: https://argoproj.github.io/argo-workflows/retries/
- Forgejo architecture: https://forgejo.org/docs/latest/contributor/architecture/
- Forgejo Actions security and runner selection: https://forgejo.org/docs/latest/user/actions/security/
- GitLab Runner architecture/executor model: https://docs.gitlab.com/development/architecture/

## Current conclusion

Brain's conceptual architecture is ahead of its reliability implementation. The correct next development target is not adding more features; it is converting the existing contracts into durable, testable guarantees. The highest-value work is the reliability foundation, full cinema evidence gate, secure Brain Git boundary, and capability-based executor scheduler.
