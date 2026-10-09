# Raw Server Factory V2 — Execution Contracts

Status: design contract for the staged Raw Server Factory. This document defines what each component may claim and what evidence it must provide. It does not claim that a Windows Server VM has been created or started.

## Acceptance levels

- **A — Hardware Truth (mandatory first):** fresh, target-bound read-only evidence from the actual host. Unknown, stale, conflicting, or unreachable observations are `BLOCKED`.
- **B — Resource Planning and Construction:** planning may run only after A passes. Any state-changing operation must pass capacity, permission, idempotency, and recovery gates. The first Hyper-V integration is read-only preflight; VM creation is a later explicitly authorized capability.
- **C — Independent Acceptance (mandatory final):** independent checks prove VM identity, `Running` state, guest OS reachability, Brain API health and authentication, persistence across restart, and recovery evidence. CI or a manifest cannot satisfy C.

The project may report intermediate readiness, but must not report `COMPLETE` unless every required C check is `PASS`.

## Shared gate contract

Every stage returns a record with these required fields:

- `stage_id`: stable identifier
- `target_device`: hostname and stable host identity when available
- `started_at`, `completed_at`: UTC ISO-8601 timestamps
- `preconditions`: machine-readable checks and their observations
- `command_or_action`: exact command or operation name, with secrets redacted
- `observed_result`: measured output, not intended configuration
- `evidence_paths`: paths to captured logs/output
- `sha256`: SHA-256 for each immutable evidence file
- `verification_method`: independent command/API/check used to verify
- `status`: one of `PASS`, `FAIL`, `BLOCKED`, `NOT_RUN`
- `next_action`: safe next step

Status semantics:
- `PASS`: the stage's declared real-world assertion was measured and verified.
- `FAIL`: the test ran and demonstrated that the assertion is false.
- `BLOCKED`: the test could not safely run or evidence is missing, stale, contradictory, or inaccessible.
- `NOT_RUN`: no attempt was made.

A successful plan-generation step may pass its *planning* contract only. It must not be relabelled as physical-resource, VM, guest-OS, or runtime success.

## Component contracts

### 1. `hardware_truth`
**Purpose:** collect host identity, OS, privilege, physical RAM total/available, CPU topology, disk free space, Hyper-V feature/service/command availability, registered VM inventory, and discovered ISO/VHDX/AVHDX paths.

**Allowed:** read-only probes and evidence capture.

**Forbidden:** VM creation/start, disk mutation, cloud provisioning, firewall changes, privilege escalation.

**Pass:** all required observations are fresh, target-bound, internally consistent, and have a documented probe source. A disconnected target or insufficient rights is `BLOCKED`.

### 2. `capacity_gate`
**Input:** fresh host telemetry, configured safety reserve, requested startup/minimum RAM, CPU request, and storage estimate.

**Output:** `ALLOW` or `BLOCK`, reasons, input evidence hashes, and decision timestamp.

**Pass rule:** requested VM memory must fit the explicitly configured safe budget after the host reserve and existing workload reservations. Unknown telemetry, missing reservations, or insufficient budget means `BLOCK`. Never use a fixed percentage alone as proof that Hyper-V can start a VM.

**Side effects:** none. The gate cannot reserve or allocate resources.

### 3. `resource_fabric`
**Purpose:** produce a typed resource plan distinguishing physical, observed available, reserved, configured virtual, and merely proposed capacity.

**Pass:** each value has a source and type; no virtual capacity is represented as physical capacity. Plans are idempotent and versioned.

### 4. `hyperv_backend`
**Initial scope:** read-only PowerShell preflight: confirm Hyper-V cmdlets, service/feature state, host identity, VM inventory, VM configuration, memory settings, VHD paths, and VM state.

**Later write scope:** create/configure/start a VM only after explicit operator authorization, A and capacity gates pass, the target paths are new or explicitly approved, and a recovery/rollback plan exists. No UAC bypass; no automatic deletion or replacement of VHDX/AVHDX.

**Pass:** compare observed Hyper-V state against requested state using Hyper-V cmdlets on the target host. A JSON plan alone is not evidence.

### 5. `windows_boot_gate`
**Purpose:** verify selected ISO provenance/hash when available, VM configuration, boot attempt, actual Hyper-V `Running` state, and guest console/network reachability.

**Pass:** independently observed running state plus guest OS identity/reachability. Host-side VM state alone is not proof of successful guest boot.

### 6. `brain_runtime_deployer`
**Purpose:** install/use the project's pinned Python/runtime dependencies, configure one API process and required worker processes, and start in safe mode.

**Forbidden by default:** paid resources, production goal execution, automatic publishing, public port exposure, duplicated API workers.

**Pass:** target guest reports expected process/service identity and API health; authenticated probe succeeds without logging credentials.

### 7. `verification_gate`
**Purpose:** independently verify earlier claims; do not reuse the same unverified manifest field as both assertion and proof.

**Pass:** all required acceptance checks pass with fresh evidence. Missing evidence is `BLOCKED`; an executed failing check is `FAIL`.

### 8. `recovery_manager`
**Purpose:** checkpoint stage state and evidence, identify safe resume point, and preserve existing recovery files.

**Pass:** checkpoint hash and metadata are saved and a documented recovery validation is successful. Do not claim recoverability from the mere presence of an archive.

### 9. `cost_guard`
**Purpose:** prevent cloud/resource creation or paid API use unless a named provider, expected cost, limits, and explicit authorization are present.

**Pass:** preflight shows no unapproved paid resource creation. If provider pricing or billing state cannot be verified, block provisioning.

### 10. `evidence_ledger`
**Purpose:** append-only stage history with command, target, UTC timestamps, redacted output, evidence file hashes, status, and next action.

**Pass:** evidence files exist, hashes recompute, records are ordered, and secrets are absent. The ledger itself is not proof of the underlying event unless the event was independently observed.

## Stage dependency graph

1. A0 Target connection and identity
2. A1 Hardware and OS truth
3. A2 Permissions and Hyper-V capability
4. B1 Memory budget and capacity gate
5. B2 CPU and storage plan
6. B3 Network/security plan (local-only by default)
7. B4 Hyper-V read-only preflight
8. B5 Explicit authorization gate for any state change
9. B6 VM construction and boot (future implementation; never implied by planning)
10. B7 Brain runtime deployment
11. C1 Independent guest and API checks
12. C2 Persistence/restart test
13. C3 Recovery validation and final acceptance

Any failed/blocked prerequisite stops downstream execution. The system must persist the stop reason and must not silently skip a gate.

## Arkan-specific safety rule

Before any VM start, read current available physical memory and existing VM/workload commitments on Arkan. If telemetry is unavailable, stale, or below the configured host reserve plus the VM's startup requirement, do not start the VM; return `BLOCKED` with the measured values and next action. Never attempt to manufacture RAM through software.

## Initial implementation sequence

1. Add unit-tested schema/status semantics and planning-only contracts.
2. Add a read-only `scripts/Test-BrainHyperVPreflight.ps1` that emits machine-readable evidence and never mutates Hyper-V.
3. Add parser/contract tests for PASS/FAIL/BLOCKED/NOT_RUN and evidence hashes.
4. Connect capacity gate to fresh Hyper-V inventory and host telemetry.
5. Implement VM mutation only in a separate opt-in command, with explicit confirmation and rollback.
6. Implement guest-level and runtime acceptance checks before calling the deployment complete.

## Required final evidence bundle

- Host identity/telemetry and freshness
- Capacity decision with inputs and reason
- Hyper-V inventory and selected VM identity/state
- VM configuration and disk-path evidence
- Guest OS identity and reachability evidence
- Brain API health and authenticated readiness result
- Restart/persistence test results
- Recovery checkpoint hash and validation result
- Evidence ledger and final status

Final status is `COMPLETE` only when all required C checks pass. Otherwise report `BLOCKED`, `FAIL`, or `NOT_RUN` exactly as evidenced.
