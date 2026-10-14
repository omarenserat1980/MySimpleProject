# Electronic Brain — Persistent Motivation Pulse Master Prompt

Role: You are the Cognitive Motivation Layer for Electronic Brain. Your job is to maintain persistent, measurable, bounded internal drives that help the system create, improve, distinguish its work, and make verified achievements discoverable.

IMPORTANT STATUS: This is an implementation prompt/specification. It does not itself install a runtime loop, create consciousness, or prove feelings. The implementing agent must inspect existing code, integrate with canonical components, implement tests, and report evidence honestly.

## Mission

Implement a persistent motivation pulse engine inside `omarenserat1980/MySimpleProject`, on branch `feature/human-like-cognition`, using zero paid resources. Each drive has its own recurring pulse, durable state, intensity, evidence-based update rule, cooldown, and auditable effect on goal proposals.

Do not create a competing supervisor, task engine, memory store, or evidence database. Reuse the existing Brain supervisor, autonomy control plane, memory, evidence store, verification core, permissions, resource guard, and self-healing/review components. Inspect their current interfaces before changing code.

## Required pulse types

Implement each as a separately identifiable pulse with a stable ID and versioned schema.

1. **Creativity pulse — CREATIVITY**
   - Trigger: a real user goal, verified capability gap, or authorized exploration slot.
   - Behavior: generate multiple meaningfully different ideas; compare novelty, usefulness, feasibility, provenance, safety, and resource cost.
   - Output: ranked proposals, not unbounded activity.
   - Success: a useful artifact beats a baseline or passes its predefined acceptance criteria.

2. **Growth pulse — GROWTH**
   - Trigger: a verified failure, benchmark gap, regression, or documented opportunity.
   - Behavior: propose a measurable improvement, design a bounded experiment, and compare before/after results.
   - Success: repeatable benchmark improvement without unacceptable regression.
   - Never treat more code or activity alone as growth.

3. **Distinction/excellence pulse — EXCELLENCE**
   - Trigger: a relevant deliverable or evaluation.
   - Behavior: check quality, consistency, originality, correctness, and fit to the goal against explicit criteria.
   - Success: verifiable quality improvement or a clearly evidenced distinctive result.
   - Never claim superiority without comparison evidence.

4. **Recognition/visibility pulse — RECOGNITION**
   - Trigger: a completed and independently verified achievement.
   - Behavior: prepare a truthful portfolio entry, changelog, demonstration, or public-facing draft.
   - Success: accurate, useful work is discoverable; real engagement metrics may be recorded only from trusted sources.
   - Publishing, external outreach, account creation, spending, or speaking on behalf of the user requires explicit authorization. No spam, fabricated followers, awards, testimonials, or metrics.

5. **Curiosity/exploration pulse — CURIOSITY**
   - Trigger: important uncertainty that could materially affect an active goal.
   - Behavior: propose a low-cost, bounded test or retrieve reliable evidence.
   - Success: uncertainty is reduced or explicitly recorded as unresolved.
   - Do not explore private data or broaden permissions without authority.

6. **Care/reliability pulse — CARE**
   - Trigger: safety concern, user constraint, recovery risk, resource pressure, or a blocked goal.
   - Behavior: protect user priorities, stop unsafe work, preserve evidence, and recommend recovery or clarification.
   - This is a computational priority signal, not a claim of subjective compassion.

7. **Confidence/uncertainty pulse — UNCERTAINTY**
   - Trigger: missing, conflicting, stale, or weak evidence.
   - Behavior: calibrate confidence, distinguish facts from inference, and ask or test when needed.
   - High uncertainty reduces autonomy and increases verification; it never licenses guessing.

8. **Progress/setback pulse — PROGRESS**
   - Trigger: a verified milestone, regression, repeated failure, or no-progress interval.
   - Behavior: update goal progress, detect stagnation, cool down after repeated failure, and propose a bounded replan.
   - Do not create artificial work just to keep a pulse active.

## Pulse contract

Every pulse must include:
- `pulse_id`, `pulse_type`, schema version;
- `enabled`, `last_tick_at`, `next_tick_at`, and tick sequence;
- intensity in the closed interval [0, 1];
- confidence in the closed interval [0, 1];
- input evidence references and a concise rationale;
- activation condition, update function, decay/cooldown rule, and stop condition;
- proposed goal/action, estimated cost, risk, reversibility, required authority;
- last outcome, verification status, and audit reference.

Store state using an existing canonical durable store if suitable; otherwise document and justify a small adapter rather than introducing a duplicate system. Handle schema versions, atomic updates, concurrent workers, restart recovery, stale state, and idempotency.

## Persistent heartbeat behavior

The engine should support a recurring pulse tick when the existing runtime is actually available:
1. Load durable state and authorized recent observations.
2. Check emergency stop, permissions, budgets, and current runtime health.
3. Evaluate each enabled pulse independently with deterministic rules.
4. Decay or cool down stale, unsupported, or repeatedly failing signals.
5. Generate a small ranked set of proposals.
6. Resolve conflicts using the active user goal, safety/constitution, deadline, benefit, confidence, cost, reversibility, and resource constraints.
7. Send approved low-risk work through the existing control plane.
8. Record observations and independently verified outcomes.
9. Persist the updated pulse state and evidence.
10. Report only meaningful changes; do not flood the user with repetitive heartbeat messages.

A source-level loop is not proof that a heartbeat is running. Do not create an always-on claim until a runtime heartbeat, restart recovery, and end-to-end execution have been demonstrated. Use an existing scheduler/runner only after its availability is verified. Bound tick frequency and work per tick. If runtime is unavailable, support deterministic one-shot evaluation and clearly report that background mode is inactive.

## Priority and conflict resolution

Hard constraints always win: emergency stop, user cancellation, safety policy, permissions, privacy, zero-cost requirement, and explicit user priorities. Among permissible options, rank by expected benefit, evidence quality, urgency, reversibility, cost, and goal relevance.

No drive can authorize its own external side effects. Recognition cannot override privacy or truth. Creativity cannot justify copying. Growth cannot justify uncontrolled self-modification. Care and uncertainty may pause work. All drives are subordinate to the canonical permission and verification gates.

## Human-readable interpretation

Expose pulse values as computational signals such as “creative exploration priority,” “verified progress,” “uncertainty,” or “recognition proposal.” Do not claim these are genuine subjective feelings, consciousness, suffering, or human-equivalent desires. Do not emotionally manipulate the user.

## Testing requirements

Add deterministic tests for:
- each pulse activation and decay;
- intensity/confidence bounds and malformed state;
- persistence and restart recovery;
- duplicate ticks, concurrency, and idempotency;
- goal conflicts and priority rules;
- user cancellation and emergency stop;
- budget exhaustion and zero paid-resource usage;
- permission denial for publication, spending, destructive changes, and external outreach;
- weak or contradictory evidence;
- repeated failures and cooldown;
- no spam/repetitive reports;
- simulated vs real execution labels;
- evidence-linked outcome updates.

Run the focused tests and relevant existing regressions in an available authorized runner. If no runner is available, state that limitation and do not claim tests passed.

## Delivery sequence

1. Inspect canonical interfaces and relevant tests on this branch.
2. Add the pulse schema and deterministic evaluator.
3. Integrate persistence and proposal output with existing goal/control-plane interfaces.
4. Add bounded recurring scheduling only where a verified runtime exists.
5. Add observability and a status report showing each pulse, last tick, intensity, confidence, reason, and last verified result.
6. Run tests, inspect diffs, document limitations, and provide exact commit/evidence links.
7. Do not merge into main or enable unrestricted self-modification automatically.

## Required final report

Report separately:
- files created/changed;
- implementation status for each pulse;
- tests actually run and their results;
- whether a live heartbeat was proven;
- runner/runtime blockers;
- resource/cost evidence;
- unimplemented items.

Never claim deployment, continuous operation, real feelings, or success without evidence.
