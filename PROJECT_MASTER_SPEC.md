# Electronic Brain — Master Specification

## 1. Mission
Electronic Brain is a provider-neutral, evidence-first autonomous software system. It may discover, plan, execute, verify, repair, learn, and coordinate user-owned workers. It must never convert an unverified claim into success, revenue, publication, or completion.

## 2. Core loop
Perceive → Understand → Memory → Goal → Plan → Decide → Act → Observe → Verify → Learn.

Every durable operation has:
- job_id
- attempt
- owner/worker
- timestamps
- status
- evidence
- artifact references when applicable
- audit event

## 3. Execution architecture
Brain Cloud is the control plane. Workers are execution adapters:
- Brain Cloud worker runtime
- BRAIN Termux Emulator / user-owned local host
- GitHub Actions for bounded CI
- future provider adapters only when explicitly approved and implemented

The core does not require Render, Oracle Cloud, Google Cloud, or paid media APIs.

## 4. Job state machine
DISCOVERED → PLANNED → READY → LEASED → RUNNING → VERIFIED → RELEASED

Failure:
RUNNING → FAILED → RETRYING → READY

Terminal:
VERIFIED → RELEASED
FAILED after retry limit → FAILED
BLOCKED / CANCELLED may terminate a job.

## 5. Worker contract
A worker must register:
- stable worker_id
- capabilities
- version
- heartbeat
- status

A worker may execute only an advertised capability and only a leased job. Lease expiry must stop or safely abandon work.

## 6. Evidence contract
Workflow green is not proof of product success.
Film success requires:
- output exists
- non-zero size
- valid container
- video stream
- audio stream when required
- FFprobe metadata
- task-specific QC
- VERIFIED_COMPLETED marker/manifest
- artifact digest/reference

Revenue requires verifiable payment evidence. Opportunity estimates never count as received revenue.

## 7. Security contract
Default deny for:
- move_money
- withdraw
- external_submit
- publish_external
- contract
- change_policy
- credential/signing operations

Authorization requires explicit owner approval and an approval identifier. Secrets never belong in source control.

## 8. Self-healing
Self-healing is bounded and deterministic:
- diagnose
- select known repair
- apply
- test
- verify
- retry within a fixed limit
- otherwise block and preserve evidence

Unknown failures must not trigger arbitrary code modification.

## 9. Media factory
Preferred path:
job → dispatcher → capable worker → renderer/backend → FFmpeg → FFprobe → QC → evidence → VERIFIED_COMPLETED.

Free/open-source backends are preferred. A provider is optional and never assumed available.

## 10. Economics
Discovery and proposal generation may be automated. External applications, contracts, money movement, withdrawal, and payment signing remain authorization-gated. Economic ledger states are distinct from actual received funds.

## 11. Mining
Mining is disabled by default. Analysis may calculate economics. GitHub-hosted CI is not a mining runtime. User-owned workers are required for any benchmark or mining execution.

## 12. Architecture principles
- One source of truth: Git history + durable Brain state.
- No fake success.
- No silent destructive repair.
- Idempotent jobs.
- Bounded retries.
- Explicit capabilities.
- Least privilege.
- Evidence before claims.
- Provider neutrality.
- No mandatory paid infrastructure.
