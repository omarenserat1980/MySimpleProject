---
name: github-repo-audit
description: Inspect a GitHub repository to understand its current architecture, recent changes, workflows, tests, runtime dependencies, and unresolved blockers before proposing changes.
---

# Brain GitHub Repository Audit

Use this skill when the user asks Brain to inspect, assess, diagnose, or understand a GitHub repository.

## Workflow

1. Establish the repository and branch/ref from the user request or current context.
2. Read repository instructions and the README before changing anything.
3. Inspect recent commits, open pull requests, relevant workflows, and the files directly related to the user's goal.
4. Search for the exact feature, error, endpoint, workflow, or symbol named by the user before broad exploration.
5. Separate verified working behavior, code that exists but is unverified, current failures, missing runtime dependencies, and blockers requiring a human or external service.
6. Trace important claims to concrete files, commits, workflow runs, or test evidence.
7. Never infer a live deployment, public HTTPS endpoint, payment, or successful runtime operation from source code alone.
8. Produce a concise evidence report with current state, findings, blockers, and the safest next action.

## Mutation boundary

This skill is read-only. Do not edit, merge, delete, deploy, publish, or trigger external side effects unless the user explicitly requests a separate mutation workflow.
