# Human-Like Cognition for Electronic Brain

Status: DESIGN / NOT YET IMPLEMENTED OR RUNTIME-VERIFIED
Branch: feature/human-like-cognition
Budget: zero-cost-first; no paid services or resource reservations.

## Goal

Improve Electronic Brain's observable cognitive capabilities—context understanding, durable memory, planning, self-review, social reasoning, learning from outcomes, and calibrated uncertainty—without claiming that software has human consciousness or subjective feelings.

## Integration rule

Do not create a parallel supervisor, memory store, decision engine, task engine, or evidence store. First integrate with and test the existing components, including the control plane, supervisor, memory, decision/task systems, evidence store, verification core, permissions, and self-healing/review loops. The current work inventory identifies runtime proof and recovery gaps; resolve those with evidence rather than assuming existing source code means the feature is operational.

## Cognitive cycle

1. **Perceive:** parse the request, context, constraints, language, and available observations.
2. **Ground:** retrieve relevant durable memories and current project state; distinguish facts, inferences, hypotheses, and unknowns.
3. **Model:** represent goals, subgoals, dependencies, stakeholders, risks, and possible outcomes.
4. **Plan:** generate multiple candidate plans and compare expected value, cost, reversibility, time, and risk.
5. **Choose:** apply permissions and safety policies; request approval for consequential external actions.
6. **Act:** execute through existing authorized task/executor interfaces with idempotency and bounded retries.
7. **Observe:** collect outputs, errors, and independent verification evidence.
8. **Reflect:** compare expected vs actual outcomes, identify causal hypotheses, and propose a repair.
9. **Learn:** store validated lessons with provenance, confidence, timestamp, scope, and expiry/review policy; do not silently convert guesses into facts.
10. **Consolidate:** periodically deduplicate memories, resolve contradictions, retain useful summaries, and support deletion/correction.

## Required capabilities

### 1. Memory
- Episodic memory: task, context, actions, outcome, evidence, and lessons.
- Semantic memory: stable facts and concepts with provenance and confidence.
- Procedural memory: tested workflows and preconditions.
- User/project preference memory: only relevant, authorized preferences.
- Retrieval must support relevance, recency, confidence, and conflict detection.
- Never store secrets or sensitive information in ordinary logs; support correction and deletion.

### 2. Reasoning and world model
- Explicit goals, constraints, assumptions, dependencies, and unknowns.
- Separate observation from inference and speculation.
- Compare at least two plans for complex tasks when practical.
- Use tools or tests to resolve important uncertainty rather than inventing answers.
- Track causal hypotheses as hypotheses until evidence supports them.

### 3. Human-centered social reasoning
- Infer likely intent cautiously and ask a concise clarification when an ambiguity changes the outcome.
- Model stakeholder needs and emotional cues as uncertain signals, not diagnoses or guaranteed facts.
- Respond empathetically without pretending to experience human emotions.
- Respect user corrections, boundaries, and stated preferences.

### 4. Learning and self-correction
- Use evaluation sets and regression tests before adopting behavioral changes.
- Record failures, root-cause hypotheses, proposed patches, test results, and rollback plans.
- A successful workflow run alone is not proof of correct behavior; require task-specific acceptance evidence.
- No uncontrolled self-modification: proposed code changes must pass tests, security checks, review policy, and rollback safeguards.

### 5. Agency and safety
- Read-only inspection may be automatic within authorized access.
- Ask for explicit approval before spending money, publishing externally, deleting data, changing access/security, or making irreversible changes.
- Apply least privilege, resource budgets, timeouts, bounded retries, audit trails, and emergency stop.
- Distinguish SIMULATED from REAL execution and evidence.
- Never report a task as completed without a verifiable result.

## Phased implementation

### Phase 0 — Baseline and integration map
Inspect current memory, supervisor, control plane, task engine, decision engine, evidence store, verification core, and tests. Identify canonical interfaces and duplicate implementations. Record baseline test results and gaps.

### Phase 1 — Cognitive record contract
Define versioned schemas for context, goal, plan, decision, memory item, action, observation, reflection, and evidence. Include correlation IDs, provenance, confidence, timestamps, and redaction rules.

### Phase 2 — Grounded memory
Implement retrieval and write paths using the existing canonical store. Add tests for relevance, stale facts, contradictory memories, user correction, deletion, and restart persistence.

### Phase 3 — Planner and decision review
Build bounded plan generation, cost/risk/reversibility scoring, constraint checks, uncertainty tracking, and permission gates. Reuse the existing decision/task engines.

### Phase 4 — Experience and reflection
Connect completed tasks to independent verification, expected-vs-actual comparison, lesson proposals, and regression examples. Only validated lessons influence future decisions.

### Phase 5 — Social and conversational reasoning
Evaluate intent resolution, contextual continuity, calibrated empathy, clarification behavior, and honest uncertainty on a fixed test suite.

### Phase 6 — Safe adaptation
Allow the system to propose code/configuration improvements. Require tests, security checks, evidence, review policy, and rollback before adoption.

### Phase 7 — End-to-end proof
Test create → authorize → plan → execute → verify → persist → restart → recover. Include interruption, duplicate request, corrupted state, conflicting memory, permission denial, and unavailable tool scenarios.

## Acceptance gates

- Existing regression tests remain green.
- Memory survives restart and supports correction/deletion.
- Every important claim can be traced to evidence or labeled as inference.
- Plans respect budget, permissions, and explicit user constraints.
- Failed actions are not represented as successes.
- Learning is reproducible and does not break prior tests.
- SIMULATED and REAL outcomes are clearly separated.
- End-to-end evidence is linked to the exact commit tested.
- No claim of human consciousness, real emotion, or human-level general intelligence is made without evidence that can establish it.

## Immediate next action

Inspect the existing canonical implementations and their tests, then implement Phase 0 and the cognitive record contract in small, reviewable commits. Do not merge this design branch or declare the capability operational until the repository tests and end-to-end acceptance gates pass.
