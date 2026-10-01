# Electronic Brain — Project Master Specification

## 1. Purpose
Electronic Brain is an evidence-first automation platform whose source of truth is this GitHub repository. It is designed to inspect, plan, execute, verify, repair, retry, and document work without declaring success unless runtime evidence supports the claim.

## 2. Core principles
- GitHub repository and committed code are the source of truth.
- Never treat file existence, a green planning step, or a queued run as proof of completion.
- Every autonomous action must have bounded scope, observable evidence, and a verifiable result.
- External side effects such as publishing, payments, withdrawals, or applications require explicit authorization.
- Free/open-source infrastructure is preferred; the current cloud control plane is GitHub-hosted Actions.
- Recovery must be idempotent where possible and must not create infinite retry loops.

## 3. Major subsystems
- Brain Core / orchestration
- Memory and audit state
- Decision and task engines
- Supervisor and self-healing
- Causal/runtime diagnostics
- Media Engine and Cinematic Factory
- Quran knowledge/reasoning layer
- Device Bridge / BRAIN Termux Emulator
- GitHub Cloud runner
- Economic Ledger and opportunity workflows
- Verification, security, health, and recovery

## 4. Task lifecycle
PENDING -> RUNNING -> SUCCESS | FAILED | CANCELLED | RETRYING

A task may only enter a terminal success state after its declared verification contract passes.

## 5. Autonomous recovery contract
The Supervisor follows:
discover -> plan -> select_backend -> execute -> verify -> repair -> retry -> deliver

Recovery is bounded by attempt/cycle limits and uses classified failures rather than blind reruns.

## 6. Cinematic verification
A movie is not considered production-complete because a workflow succeeds. The intended evidence chain is:
Render -> QC -> FFmpeg -> Master QC -> final.mp4 -> VERIFIED_COMPLETED

The final state requires a real artifact plus machine-readable media evidence.

## 7. Cloud execution
GitHub Actions provides ephemeral Linux runners. They are not persistent virtual machines. Persistent state must therefore be stored in repository artifacts/state or another explicitly configured durable layer.

## 8. Change discipline
Changes should follow:
inspect -> backup/evidence -> smallest safe change -> tests -> verify -> commit -> rerun -> inspect result

## 9. Security
Tokens and secrets must never be committed. Autonomous workflows must use least-privilege permissions and must not infer financial success from an unverified ledger entry.

## 10. Current implementation status
The repository contains the major Brain V12 modules and 31 workflows at the time of this specification. Runtime audits remain authoritative for what is actually working.
