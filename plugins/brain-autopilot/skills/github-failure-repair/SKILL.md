---
name: github-failure-repair
description: Diagnose a GitHub Actions, test, build, import, deployment, or runtime failure and prepare the smallest evidence-backed repair.
---

# Brain GitHub Failure Repair

Use this skill when the user reports a GitHub, CI, test, build, import, deployment, or runtime failure.

## Workflow

1. Identify the exact repository, workflow/run/job, commit, error text, or failing test.
2. Fetch the relevant logs and source files. Do not diagnose from a truncated snippet when the surrounding context is available.
3. Find the first actionable failure rather than treating downstream cascade errors as independent root causes.
4. Trace the failing symbol/configuration through imports, environment variables, workflow inputs, paths, and tests.
5. Propose the smallest repair that preserves unrelated behavior.
6. Before mutation, state the intended files and why they are sufficient.
7. After mutation, re-read the changed files and run the narrowest relevant tests/workflow checks available.
8. If execution is unavailable, mark the repair as unverified instead of claiming success.
9. Do not weaken tests, remove security gates, suppress errors, or fabricate credentials to make CI green.

## Safety

Treat writes, workflow dispatches, merges, deployments, and destructive operations as side effects. Require explicit user authorization for them. Preserve an audit trail of the intended change and verification evidence.
