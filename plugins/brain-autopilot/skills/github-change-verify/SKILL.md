---
name: github-change-verify
description: Make a focused authorized GitHub code change, verify it with repository-native checks, and report exact evidence without claiming more than was tested.
---

# Brain GitHub Change and Verification

Use this skill when the user explicitly asks Brain to implement, fix, update, or verify a repository change.

## Required loop

Inspect -> Plan -> Change -> Test -> Verify -> Report

1. Inspect the target files and repository instructions first.
2. Preserve unrelated work and prefer a focused patch.
3. Apply only the authorized change.
4. Re-read the changed area.
5. Run the most specific available tests first, then broader checks when practical.
6. Inspect actual GitHub Actions results when CI is triggered.
7. Confirm the resulting commit/ref and relevant artifacts.
8. Report exact files changed, tests/checks actually executed, workflow/run evidence, and remaining warnings or blockers.
9. Distinguish implemented, tested, CI-passed, deployed, and live-verified. They are not interchangeable.

## Evidence gate

A green local test does not prove a production deployment. A successful GitHub workflow does not prove a persistent runtime. A generated file does not prove that a user-facing feature is reachable.

Never claim VERIFIED_COMPLETED without the evidence required by the repository's own acceptance criteria.
