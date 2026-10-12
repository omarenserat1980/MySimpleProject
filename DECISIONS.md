# Electronic Brain — Decisions

## D-001 — GitHub is the source of truth
Keep primary project state in GitHub; code, workflow definitions, commits, and Actions evidence must be inspectable and reproducible.

## D-002 — No paid Render dependency
Do not make Render a required runtime dependency. Keep a free/no-card path and portability.

## D-003 — GitHub-hosted Linux for bounded cloud execution
Use GitHub Actions runners for bounded execution. Runners are ephemeral; persistent state must not depend on runner disk.

## D-004 — Evidence before success
A green workflow is not sufficient evidence of a completed product artifact.

## D-005 — Bounded self-healing
Autonomous repair uses explicit failure classes and bounded cycles.

## D-006 — External side effects require authorization
Publishing, financial movement, withdrawals, and similar external actions remain permission-gated.

## D-007 — Free/open-source media first
Prefer local/open-source rendering, FFmpeg, Pillow, and free runtime components.

## D-008 — Module-safe CI execution
Run Python package modules importing brain_v12 with `python -m ...` in CI.

## D-009 — Preserve legacy requirements
Retain and migrate legacy requirements rather than silently deleting them.

## D-010 — Pytest is canonical
Use pytest for Brain tests and fail CI when the suite cannot run.

## D-011 — Runtime synchronization is explicit and convergent
Use stable record identity, monotonic revisions, idempotent event IDs, optimistic concurrency, durable tombstones, replayable events, and deterministic state digests.

## D-012 — Autonomous Company Mode
Brain may autonomously perform reversible, evidence-verifiable, legally non-binding work. Contracts, funds, withdrawals, legal filings, protected credentials, and destructive actions remain gated. Technical autonomy never implies legal authority.

## D-013 — Software-only execution is mandatory
Decision: Brain's execution registry accepts software workers only. Physical-device, Android, Termux, and hardware worker registration is rejected. The legacy adapter-enable flag cannot override this policy.

Reason: Brain must not depend on Arkan, phones, user-owned PCs, Hyper-V, or self-hosted physical runners for core operation. Virtual CPU, memory, storage, network, power, and thermal behavior must be labeled simulated unless independently calibrated.

Constraint: Software-only does not imply unlimited compute or prove that every external workflow is hardware-independent. A task still needs executor output and independent evidence gates.
