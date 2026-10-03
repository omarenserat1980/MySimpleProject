---
name: brain-github-orchestrator
description: Orchestrate a complete Brain repository task by discovering the goal, choosing the right GitHub workflow, executing authorized changes, and closing the loop with evidence.
---

# Brain GitHub Orchestrator

Use this skill for end-to-end repository work when the user says to proceed, fix it, inspect it, or complete the task without specifying every intermediate step.

## Decision loop

1. Translate the user's request into a concrete repository goal.
2. Inspect current state and identify the smallest missing capability.
3. Select github-repo-audit for discovery, github-failure-repair for failures, or github-change-verify for authorized implementation.
4. Execute sequentially; do not skip evidence gates.
5. If a required external dependency is unavailable, complete all repository-side work that can be completed safely and isolate the external blocker.
6. Re-check the repository after each meaningful mutation.
7. Stop when the acceptance criteria are met or when the next step requires unavailable credentials, an offline device, a human approval, or a real external runtime.
8. Summarize what Brain actually completed and what remains.

## Core rule

Autonomy means fewer unnecessary questions, not permission to invent capabilities or success.
