# Brain Second-Agent Coordination

Status: ACTIVE
Purpose: Shared execution handoff between the primary Brain orchestrator and the second execution device/agent.

## Operating rules

- GitHub is the shared source of truth.
- Work on branches; do not modify `main` directly for experimental or repair work.
- Every execution claim must include evidence: command/test result, commit SHA, workflow run, or PR.
- Never place passwords, API keys, tokens, runner credentials, Azure secrets, or private identifiers in this file.
- Azure actions are READ-ONLY until explicit human approval for resource creation and cost.
- Prefer free-first infrastructure and preserve the zero-cost constraint.
- Keep one authoritative orchestration path; do not create competing autonomous loops.

## Current task

### Primary orchestrator
- Coordinate the second agent through this file.
- Review its evidence.
- Define the next bounded task.
- Accept/reject work based on evidence.

### Second agent
- Inspect this file before starting work.
- Execute the current task on an isolated branch/worktree.
- Record results below.
- Commit code changes and report the commit SHA.
- Do not merge to `main` autonomously.

## Current handoff

Task: Validate and advance the Home Server integration (PR #200) and investigate why its GitHub Actions checks are not appearing.

Constraints:
- Do not provision Azure resources.
- Do not expose or modify secrets.
- Do not reset or clean unrelated working trees.
- Run tests in a clean environment where possible.

## Evidence log

### 2026-10-09
Primary orchestrator established this coordination channel.

Pending second-agent report:
- Repository/branch inspected:
- Tests executed:
- Test result:
- GitHub Actions result:
- Problems found:
- Repairs made:
- Commit SHA:
- PR:
- Recommended next action:

## Next task
Leave this section updated with exactly one bounded task for the second agent.

Current next task:
Investigate PR #200 workflow discovery/execution and produce a reproducible PASS/FAIL result for the Home Server tests without changing `main`.
