# Brain Operations Timeline — 2026-10-08

This record captures the material recovery/runtime changes completed during the stabilization session.

## Verification and runtime
- Verified local Brain API on 127.0.0.1:8012.
- Verified the Termux Emulator agent identity is redmi3-01.
- Verified the local supervisor is single-instance and producing VERIFIED cycles.
- Identified that /health reports cloud-worker attestation, while Brain liveness is assessed separately.
- Identified Android Executor staleness as an executor dependency issue, not proof that Brain core is dead.

## Stabilization fixes
- Fixed evidence-gated completion in CognitiveLoop.
- Hardened TaskEngine.verify_and_complete so a truthy FAILED mapping cannot complete a task.
- Canonicalized cognitive evidence hashing through EvidenceStore.digest.
- Corrected supervisor reporting so verified execution is recorded as VERIFIED.
- Added supervisor recovery when the API is already listening.
- Removed duplicate fcntl import.

## Runtime recovery incident
- A stale Git worktree under .brain/runtime was detected and pruned.
- Supervisor was intentionally stopped only for controlled repair and then relaunched.
- The live supervisor subsequently returned VERIFIED cycles.
- No uncontrolled parallel supervisor was allowed; the single-instance lock remains authoritative.

## Golden checkpoint
- Golden checkpoint ID: BRAIN-GOLDEN-01.
- Source commit: 343280f2884079655f33f2264f27f5c283cf74b0.
- Checkpoint branch: checkpoint/brain-golden-01-2026-10-08.
- Checkpoint manifest is versioned in recovery/BRAIN_GOLDEN_CHECKPOINT_01.json.

## Recovery layer
PR #155 added and merged:
- Recovery architecture documentation.
- Termux operations documentation.
- Desktop Commander configuration documentation.
- Brain runtime/state inventory.
- Safe live-state snapshot utility.
- State snapshot documentation.
- Golden recovery workflow.

Merge commit for the recovery/documentation layer:
6490e81674f906521cbf14ff402cbdd02bbc5f9b

## Important architectural rule
The Golden source commit is the restoration anchor. Future main-branch development does not invalidate it. The recovery workflow resolves the checkpoint manifest and checks out the exact stored source SHA rather than assuming current main is the checkpoint.

## Secrets
No agent key, control key, OAuth token or other secret value is included in Git documentation or recovery artifacts.

## Remaining recovery dependency
The live production state databases and queues live on the runtime host and are not automatically visible to a GitHub-hosted runner. The new snapshot utility can capture them on the runtime host or a trusted self-hosted runtime runner. This is the next state-backup integration point.
