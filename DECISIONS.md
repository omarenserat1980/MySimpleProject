# Electronic Brain — Decisions

## D-001 — GitHub is the source of truth
Decision: Keep the primary project state in the GitHub repository.

Reason: Code, workflow definitions, commits, and Actions evidence are inspectable and reproducible.

## D-002 — No Render dependency
Decision: Do not make Render a required runtime dependency.

Reason: The project direction requires a free/no-card path and the Brain must remain portable.

## D-003 — GitHub-hosted Linux as the free cloud control plane
Decision: Use GitHub Actions runners for bounded cloud execution.

Constraint: Runners are ephemeral. Persistent state must not depend on local runner disk.

## D-004 — Evidence before success
Decision: A workflow being green is not sufficient evidence of a completed product artifact.

Reason: The Brain must distinguish orchestration success from verified output.

## D-005 — Bounded self-healing
Decision: Autonomous repair uses explicit failure classes and bounded cycles.

Reason: Prevent infinite loops, uncontrolled changes, and repeated damage.

## D-006 — External side effects require authorization
Decision: Publishing, financial movement, withdrawals, and similar external actions remain permission-gated.

## D-007 — Free/open-source media first
Decision: Prefer local/open-source rendering, FFmpeg, Pillow, and free runtime components.

## D-008 — Module-safe CI execution
Decision: Python package modules that import brain_v12 should run with python -m ... in CI.

Reason: Direct file execution can remove the repository root from sys.path and produce false dependency failures.

## D-009 — Legacy ideas are preserved
Decision: Existing legacy requirements and prior architectural ideas should be retained and migrated rather than silently deleted.

## D-010 — Pytest is the canonical Brain test runner
Decision: Use pytest for the Brain test suite in GitHub Actions.

Reason: The repository tests use pytest-style test functions; unittest discovery does not reliably collect them. CI must execute the actual test files and fail when the suite cannot run.

## D-011 — Runtime synchronization is explicit and convergent
Decision: Brain runtime replicas use stable record identity, monotonic revisions, idempotent event IDs, optimistic concurrency, durable tombstones, replayable events, and deterministic state digests.

Reason: Cloud, device/emulator, and worker state must converge without silent overwrites or duplicate side effects.

Constraint: Runtime synchronization is separate from Git source synchronization; external side effects remain behind existing authorization gates.


## D-012 — Autonomous Company Mode

Decision: Brain operates as an autonomous company operating system by default for all actions that are technically reversible, evidence-verifiable, and legally non-binding.

Autonomous scope includes:
- inspect, plan, code, test, repair, verify, package, deploy, monitor, document, benchmark, optimize, and roll back;
- select among Brain-owned and free/open-source executors;
- discover and normalize business opportunities;
- prepare offers, product artifacts, customer-support drafts, delivery packages, and commercial analyses;
- continuously maintain evidence, audit trails, recovery points, and health state.

Hard gates remain for actions that can create an external legal, financial, identity, or irreversible obligation:
- signing or accepting contracts;
- creating personal guarantees or debt;
- moving company or personal funds;
- initiating withdrawals or payments;
- submitting legally binding filings;
- making regulated representations;
- disclosing protected credentials or secrets;
- irreversible deletion or destructive infrastructure actions unless a pre-authorized recovery policy explicitly permits them.

These gates are fail-closed and must never be bypassed by prompt, retry, fallback provider, or autonomous repair.

Autonomy tiers remain:
BRAIN_OWNED -> FREE_DIVERSE -> PAID_EXTERNAL.

Commercial truth remains evidence-first:
OFFER -> CUSTOMER -> CONTRACT -> DELIVERY -> PAYMENT_VERIFIED -> REVENUE_REALIZED -> COSTS -> PROFIT_VERIFIED.

Decision authority:
Brain may make internal technical and operational decisions within declared policy. External authority must be evidenced separately; technical autonomy never implies legal authority.

Objective:
Minimize routine human intervention while maximizing Brain's independent capability, recovery, auditability, and lawful commercial execution.
