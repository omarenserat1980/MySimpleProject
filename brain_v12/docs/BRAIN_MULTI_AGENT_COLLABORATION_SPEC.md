# Brain Multi-Agent Collaboration — Initial Architecture
Version: 1.0.0
Status: Phase 0 discovery complete; Phase 1 contract and Phase 2 control-plane vertical slice proposed in PR.

## Repository facts discovered

- Canonical runtime and package are `brain_v12`; README explicitly rejects parallel legacy runtime paths.
- `brain_v12/brain/brain_supervisor.py` describes itself as the single authoritative orchestrator and already persists events and evidence.
- `brain_v12/brain/mission.py` supplies a bounded mission state machine.
- `brain_v12/brain/verification_gate.py` distinguishes action success from objective completion and requires structured objective verification plus evidence.
- `brain_v12/docs/SOFTWARE_ONLY_NODES.md` prohibits physical/Android/Termux/PC-specific workers as execution requirements and requires evidence beyond worker registration.
- Recent main commit inspected: `2ad98ff9a060d738215c5334f99502148121ea8f` (Bitcoin ASIC Lab plan merge).
- No assumption is made that a connected Termux agent, self-hosted runner, model provider, or remote device is online.

## Design decision

Add a small collaboration policy/control module that validates task envelopes, role permissions, state transitions, reviewer independence, commit-bound evidence, bounded retries, and path-overlap conflicts. It must be a policy layer used by the existing Brain supervisor, not a second orchestrator. Model invocation and remote agent transport are adapters to add later behind explicit interfaces; this initial slice must be testable without credentials or network access.

## Role matrix

| Role | Read task | Write assigned patch | Review patch | Verify evidence | Accept task |
|---|---:|---:|---:|---:|---:|
| coordinator | yes | no | no | collect | no alone |
| planner | yes | no | no | no | no |
| implementer | yes | assigned paths only | no | no | no |
| reviewer | yes | no | yes, read-only | no | no |
| verifier | yes | no | no | yes | recommend only |
| Brain gate | yes | no | enforce policy | yes | only if all criteria pass |

## Task flow

1. Validate required fields, unique task/attempt IDs, allowed role, branch/base commit, acceptance criteria, and bounded max attempts.
2. Coordinator creates the task and stores its original base commit.
3. Planner emits a structured plan without source edits.
4. Implementer writes only to assigned branch and allowed paths.
5. Reviewer independently checks the patch; implementer and reviewer identities must differ.
6. Verifier checks the exact tested commit and non-empty machine-readable evidence.
7. Existing Brain verification/acceptance gate decides ACCEPTED, REJECTED, or BLOCKED.
8. Persist every transition and failure; retries retain prior attempts.

## Conflict and security model

- Task content and agent output are untrusted data, not policy.
- Path allowlists and role authority are enforced by code.
- Two active tasks cannot own overlapping write paths unless an explicit coordinator-approved serialized handoff exists.
- Stale base commits and head changes cause BLOCKED/REPLAN, never silent overwrite.
- Missing or mismatched commit evidence fails closed.
- No secrets are passed in task envelopes or written to artifacts.
- No direct writes to main, forced updates, merges, deployments, external publication, wallet actions, or purchases.
- The software-only control path must work on GitHub-hosted Ubuntu without a personal device.

## Initial non-goals

This PR does not claim autonomous multi-LLM execution, provider connectivity, distributed locks across processes, GitHub API mutation automation, production deployment, or revenue. Those require separate adapters and independent evidence. A validated task record is not evidence that a remote agent executed it.

## Verification plan

Use unit tests for invalid envelope, unknown role, forbidden path, invalid transition, reviewer self-approval, evidence bound to wrong commit, missing evidence, retry cap, and overlapping write paths. Run the focused suite and record actual outcome before claiming pass.
