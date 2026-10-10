# Electronic Brain — Portable Resource Orchestration Architecture

Status: Implementation in progress on an isolated branch; not merged or deployed.
Date: 2026-10-10

## Objective

Keep the selected host's physical CPU, RAM, disk I/O, and thermals at the lowest practical level while maximizing usable compute capacity from authorized, available, cost-approved execution providers. Make the Brain control plane and executor contract portable so a future device can be selected and enrolled without rewriting Brain.

This design does not claim that software creates physical RAM/CPU. Remote compute is a separate worker that returns results/artifacts over authenticated network interfaces.

## Non-negotiable constraints

- No paid cloud resource is created or enabled without explicit user approval.
- Prefer free, open-source, and already-authorized capacity; fail closed if no eligible executor exists.
- Preserve existing Windows Server 2025 files, recovery snapshots, and device data.
- ASUS VivoBook/Arkan is a lightweight administration/bootstrap client, not the permanent authority or default heavy-compute worker.
- No unsafe VM boot attempt on a host that lacks verified memory headroom.
- A task is not successful until independently verified evidence is stored.
- Never report a remote worker as connected, provisioned, or running without live checks.

## Logical architecture

1. **Brain Control Plane** — canonical task state, policy, permissions, decisions, run IDs, and evidence index. Keep it independent of any single host.
2. **Resource Orchestrator** — estimates each task's CPU, RAM, disk, GPU, network, duration, security class, and maximum cost.
3. **Capability/Executor Contract** — provider-neutral request and result schema; adapters for GitHub-hosted Actions, approved cloud VMs/containers, and explicitly enrolled devices.
4. **Executor Gate** — verifies identity, attestation/health, allowed capabilities, least-privilege permissions, lease/fencing token, idempotency key, and exact intent hash before execution.
5. **Evidence & Verification** — collect logs, exit status, artifact digests, test outputs, cost metadata, and timestamps; independently verify outputs before accepting them.
6. **Portable Enrollment** — any future host runs a small bootstrap agent, reports hardware/OS/capabilities, receives a unique identity, and remains untrusted until approved and health-checked.
7. **Recovery** — rebuild control plane from GitHub source plus the golden checkpoint and durable task/evidence state; workers are replaceable and must not own canonical Brain state.

## Scheduling policy

Choose an executor in this order:
1. Brain-owned and already available capacity.
2. Authorized free-tier or free hosted CI capacity within documented quotas.
3. User-owned, explicitly enrolled hardware when local-resource budget permits.
4. Paid external capacity only when the user explicitly enables it and a cost estimate is accepted.

Reject or defer tasks when no executor satisfies required capacity, permission, residency, availability, or cost constraints. Do not silently fall back to paid resources.

## ASUS low-footprint profile

- Run only the remote administration/bootstrap client and a bounded lightweight agent.
- Do not run heavy inference, video rendering, builds, or Windows Server VMs locally by default.
- Keep Windows-managed pagefile unless a measured, approved change is necessary; pagefile is not equivalent to RAM.
- Use bounded polling, concurrency, memory limits, disk quotas, and backoff.
- Transfer task payloads and artifacts by digest; avoid duplicate local copies and retain only bounded caches.
- Expose a configurable local resource budget and refuse tasks exceeding it.

## Cloud and cost gate

Before any deployment, gather subscription state, offer/benefit eligibility, regional SKU availability, quota, storage/network requirements, and a dated cost estimate including compute, disks, public IP/network egress, monitoring, and licensing. Treat unknown price or eligibility as NOT APPROVED. A quota check alone does not prove SKU capacity or free-tier eligibility.

Deployment requires a separate explicit approval after the plan and estimate are shown. Apply infrastructure changes only after approval; never destroy or replace existing resources as part of discovery.

## Portable executor contract (conceptual)

Each execution request must contain:
- schema_version, task_id, idempotency_key, intent_hash
- requested_capabilities and resource_limits
- authorization_scope and expiry/lease token
- input artifact references with SHA-256 digests
- max_cost (zero unless user approves a nonzero limit)
- timeout and cancellation policy

Each result must contain:
- task_id, executor_id, accepted intent_hash, status and exit code
- start/end timestamps and measured resource usage where available
- logs and output artifact references with SHA-256 digests
- cost metadata, verification results, and failure reason

Secrets are delivered through the provider's secret manager or short-lived identity, never committed to Git. Workers do not get unrestricted control-plane credentials.

## Acceptance tests

- A new executor can be enrolled without changing core orchestration code.
- A task is rejected when identity, permission, lease, intent hash, or cost gate is invalid.
- A paid provider cannot be selected while paid capacity is disabled.
- The scheduler defers tasks when free capacity/quota is unavailable.
- A task with no executor reports BLOCKED/NO_EXECUTOR, never success.
- A worker can be replaced while canonical task state and evidence remain intact.
- ASUS resource use stays within configured CPU/RAM/concurrency limits during idle and remote-heavy workloads.
- Windows Server 2025 is considered complete only after actual boot, remote access, health checks, and saved verification evidence.

## Implementation sequence

1. Inventory current Capability Fabric, executor adapters, DeviceBridge, cloud workflows, and evidence storage.
2. Add resource profiles and a policy-only scheduler simulation (no provisioning).
3. Add portable enrollment and the unified executor contract behind existing gates.
4. Add quota/eligibility/cost preflight with fail-closed behavior.
5. Test on GitHub-hosted free CI first; do not assume capacity is always available.
6. Add an approved cloud adapter only after user-approved cost and eligibility evidence.
7. Validate failover/recovery and ASUS low-footprint operation.

## Current evidence and open items

- Azure CLI and an enabled subscription were observed on Arkan on 2026-10-10.
- Resource group `rg-electronic-brain` exists in `eastus`; it contains `brain-env`.
- The initial Azure VM inventory returned no VMs.
- Regional vCPU usage showed 0 of 4 total regional vCPUs at the time of the check.
- These facts do not prove free-tier eligibility, current SKU capacity, or a zero-cost deployment.
- The current repository roadmap already identifies provider-neutral Capability Fabric and Brain Cloud execution; the unified executor contract and durable run/evidence index remain open items.

## Change safety

This document is a proposal only. It does not create infrastructure, modify Windows settings, change pagefile configuration, boot a VM, or enable paid services.


## Implementation status — 2026-10-10

Added on this branch:
- `brain_v12/brain/portable_resource_orchestrator.py`: deterministic policy-only planning with capability, health, permission, capacity, local-resource-budget, and cost gates.
- `brain_v12/tests/test_portable_resource_orchestrator.py`: tests for remote-free preference, local-budget enforcement, paid opt-in and ceiling, missing capability, and stable intent hashes.

The scheduler returns `PLANNED` or `BLOCKED_NO_EXECUTOR`; `PLANNED` explicitly means that no task has started. It is not yet wired into live execution and cannot provision cloud resources. Automated test results must be checked before this work is considered validated.
