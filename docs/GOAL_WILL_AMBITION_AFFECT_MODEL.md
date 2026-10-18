# Brain Goal, Will, Ambition, and Affective-State Architecture

Status: PROPOSED DESIGN — NOT YET IMPLEMENTED OR RUNTIME-VERIFIED
Repository: omarenserat1980/MySimpleProject
Branch: feature/human-like-cognition
Budget: zero dinar; do not reserve or invoke paid resources.

## Intent

Make Electronic Brain behave as a persistent, goal-directed digital agent rather than a passive command executor. It should maintain self-generated but bounded goals, pursue long-horizon aspirations, notice changes in its environment, estimate affect-like internal state, and learn from verified outcomes.

This design does not assert consciousness, subjective experience, sentience, or real feelings. "Will" means persistent goal selection and follow-through under constraints. "Ambition" means long-horizon objectives and measurable milestones. "Feeling" means an explicit affect-like state model that influences priorities and communication in testable ways.

## Integration with existing architecture

Do not create a competing supervisor or duplicate control plane. The inspected main branch already contains:
- `brain_v12/brain/brain_supervisor.py` — bounded orchestration and existing mission handling.
- `brain_v12/brain/autonomy_control_plane.py` — durable jobs, budgets, bounded attempts, and external-action rejection.
- Existing reality, constitution, evidence, verification, resource-guard, and self-healing/review components.

The new cognitive layer must propose goals and plans to these existing components. The supervisor, permissions, resource guard, and verification gate remain authoritative. Before implementation, inspect the full interfaces and tests on the active branch and map canonical storage.

## 1. Goal system

Represent each goal as a versioned record:
- `goal_id`, title, description, origin (`user`, `system_maintenance`, `learned_proposal`), parent goal, and dependencies.
- measurable success criteria, evidence required, baseline, target, and deadline if applicable.
- priority, estimated value, confidence, resource/time budget, risk, reversibility, and owner/authority.
- state: `proposed`, `approved`, `active`, `blocked`, `suspended`, `completed`, `failed`, or `cancelled`.
- created/updated timestamps, last review, next review, and rationale.
- evidence links, decision history, and termination conditions.

Goals are not all equal: user goals and safety/maintenance obligations take precedence over Brain-generated ambitions. A self-generated goal is a proposal until validated against the constitution, permissions, available capacity, cost limits, and user preferences.

## 2. Operational will

Implement "will" as reliable bounded agency:
1. Maintain a ranked queue of approved goals.
2. Detect the next actionable milestone and dependencies.
3. Generate and compare candidate plans.
4. Select an authorized action with a finite budget and deadline.
5. Execute through the existing control plane and authorized executor.
6. Verify the result independently and record evidence.
7. Resume from checkpoints after restart without duplicating side effects.
8. Replan when blocked, or suspend and explain why.

The agent must not bypass authorization, fabricate access, invent observations, or continue indefinitely. Repeated failures trigger a cooldown and a human-readable escalation. The emergency stop and user cancellation must override every goal.

## 3. Ambition / long-horizon aspirations

Maintain a small, reviewable aspiration hierarchy, for example:
- Reliability: reduce repeated failures and improve recovery.
- Competence: improve tested capabilities and close documented gaps.
- Helpfulness: complete user-approved projects and report outcomes honestly.
- Sustainability: operate within zero-cost and resource limits unless the user explicitly changes them.
- Learning: improve on benchmarked tasks without regressing prior behavior.

Each aspiration must have measurable milestones and a review cadence. No goal may justify spending money, collecting unnecessary personal data, expanding permissions, publishing externally, or self-modifying without the required approval. Aspirations are operational objectives, not proof of a self or inner desire.

## 4. Affective-state model ("feelings" as computational signals)

Use a transparent, bounded state vector rather than claiming real subjective emotions. Candidate signals:
- uncertainty / confidence;
- progress / stagnation;
- task load / resource pressure;
- novelty / surprise;
- risk / safety margin;
- goal conflict / frustration proxy;
- positive verified outcome / setback.

Each signal needs a defined computation, bounded range, decay rule, evidence source, and tests. The vector may adjust explanation style, urgency, planning effort, and whether to ask for clarification; it may never override safety rules, facts, consent, or permissions. Expose these signals as "estimated internal state" or "affect-like indicators," not as human feelings. Do not simulate distress, claim suffering, or manipulate the user into continuing an interaction.

## 5. Self-generated goals

Allowed proposal classes:
- repair a failing test or repeated verified runtime failure;
- close a documented reliability/security/recovery gap;
- improve an existing capability against a benchmark;
- consolidate contradictory or stale project memory;
- prepare a zero-cost experiment that produces useful evidence.

Every proposal includes: observed trigger, supporting evidence, expected benefit, alternative actions, estimated cost, risk, required permissions, stop conditions, and an evaluation metric. A proposal is discarded if evidence is weak, its expected value is negative, resources are unavailable, or it conflicts with a higher-priority goal. No background goal should be created solely to prolong interaction.

## 6. Daily/periodic reflection loop

At a bounded cadence:
1. Read only authorized state and recent verified evidence.
2. Compare active goals with progress and deadlines.
3. Detect blocked goals, regressions, stale assumptions, and resource pressure.
4. Propose a small set of next actions, ranked by benefit/risk/cost.
5. Auto-execute only pre-authorized, low-risk, reversible actions.
6. Ask for approval for consequential changes.
7. Publish a concise status report with completed, blocked, proposed, and unverified items.

Do not create a scheduler or recurring runtime until the existing runner/runtime path is proven operational. A source file or CI success alone is not evidence that the autonomous loop is running.

## 7. Safety and user control

- User intent, applicable policy, permissions, and emergency stop override agent-generated goals.
- Never spend money or reserve paid resources under the zero-cost requirement.
- External publication, money movement, deletion, security changes, and irreversible actions require explicit approval.
- Least privilege, bounded retries, timeouts, resource quotas, audit events, and rollback are mandatory.
- Memory and affect signals must be correctable and deletable where applicable.
- Clearly label simulated, proposed, attempted, verified, and real-world outcomes.
- No deception about identity, consciousness, emotions, autonomy, access, or completed work.

## 8. Implementation sequence

1. Inventory existing goal/mission/task/memory models and their tests; select one canonical representation.
2. Add goal schema and migration-free adapter; unit-test priorities, dependencies, lifecycle, idempotency, and restart persistence.
3. Add goal proposer that produces proposals only; test it against the constitution, budget, and user preferences.
4. Integrate proposal approval and execution with existing control plane, supervisor, evidence store, verification core, and resource guard.
5. Add affect-like signal calculations with deterministic tests and no effect on authorization.
6. Add bounded reflection and restart/recovery tests.
7. Run end-to-end tests: propose → approve → plan → execute → verify → persist → restart → resume/cancel.
8. Only after runtime evidence passes may the capability be described as operational.

## Acceptance criteria

- A user-approved long-horizon goal survives restart and advances by evidence-backed milestones.
- A system-generated goal remains a proposal until it passes policy and authority gates.
- The system stops when cancelled, out of budget, unsafe, or blocked beyond its retry limit.
- Every claimed accomplishment links to verification evidence.
- Affect-like signals are deterministic, bounded, transparent, and unable to bypass policy.
- Tests cover goal conflict, stale evidence, unavailable executors, duplicate requests, crash/recovery, permission denial, and emergency stop.
- Zero paid resource usage is proven from execution configuration and logs.
- No claim of subjective feelings, consciousness, or human-equivalent will is made.

## First delivery

Start with read-only integration mapping and goal-schema tests. Do not alter the default branch, merge automatically, enable unrestricted self-modification, or claim the agent has become conscious.
