# Brain ASIC Node — Controlled Self-Modification Plan

## Purpose

Make an existing ASIC software node maintainable by Electronic Brain without confusing a software model with fabricated silicon or verified mining. Brain may propose and test changes automatically; deployment and hardware-facing actions remain gated by explicit authorization and evidence.

## Current repository facts

- `brain_v12/brain/asic_resource_adapter.py` supports `SIMULATOR`, `REMOTE_PROVIDER`, and `PHYSICAL_DEVICE` records.
- Simulator resources are deliberately marked `SIMULATED`; real-mode telemetry is caller-supplied and remains untrusted.
- `release_gate()` remains blocked until external identity attestation exists.
- `brain_v12/asic/rtl/brain_asic_core.sv` is an RTL prototype. RTL simulation or synthesis is not proof of a fabricated ASIC or of Bitcoin mining.
- The current mining-node API reports `SIMULATOR`; it must not be relabeled `REAL` to bypass missing evidence.

## Proposed control loop

`SCAN → REVIEW → PLAN → PATCH_ON_BRANCH → TEST → VERIFY → ACCEPT_OR_REJECT`

1. **SCAN:** collect repository revision, working-tree state, device/runner identity, tool versions, resource limits, and current health. Do not emit secrets.
2. **REVIEW:** classify the requested change and affected files. Reject changes that weaken authentication, evidence gates, safety limits, or tests.
3. **PLAN:** generate a minimal patch plan with expected behavior, rollback point, and acceptance tests.
4. **PATCH_ON_BRANCH:** use a dedicated Git branch and commit; never let the autonomous agent write directly to `main`.
5. **TEST:** run unit tests first, then RTL testbench (Icarus Verilog or Verilator), synthesis checks (Yosys), and physical-design checks only when the relevant tools are installed. Missing tools must be reported as `BLOCKED_TOOL_MISSING`, not passed.
6. **VERIFY:** inspect the diff, verify artifact hashes and provenance, run security checks, and confirm the tests correspond to the exact candidate commit.
7. **ACCEPT_OR_REJECT:** create a PR for review. Reject on any failed check, stale evidence, untrusted source, or changed safety gate. Production/device deployment requires a separate explicit approval.

## Modes and trust levels

- `SIMULATION`: software-generated estimates only.
- `RTL_VERIFIED`: RTL tests and synthesis checks passed for a specific commit; not a fabricated chip.
- `DEVICE_CONNECTED_UNVERIFIED`: authenticated connection to an identified physical device, but no independent mining proof.
- `REAL_MINING_VERIFIED`: requires fresh device identity/attestation plus independent pool-side accepted-share evidence.
- `REALIZED_REVENUE_VERIFIED`: requires independently verifiable payout evidence, with costs recorded separately.

Never promote a state based on a label, local file hash alone, agent self-report, dashboard balance, or caller-supplied `verified: true`.

## Device bridge contract

A future device bridge must:
- Use an authenticated, encrypted channel and short-lived, least-privilege credentials stored outside Git.
- Accept only allowlisted, typed actions; no arbitrary shell or unrestricted remote code execution.
- Start in read-only diagnostic mode.
- Require fresh signed or authenticated heartbeat, nonce/timestamp checks, and replay protection.
- Return measured results, tool versions, device identity evidence, candidate commit SHA, and a digest of the result bundle.
- Enforce CPU/memory/temperature/time limits and a stop switch; never auto-install firmware or alter voltage/clock/power controls.
- Keep mining pool credentials and wallet secrets outside Brain's source code; never request seed phrases or private keys.
- Store an append-only audit trail and support rollback to the last known-good software version.

## Zero-budget implementation order

1. Reuse the existing ASIC adapter, evidence store, RTL testbench, and CI; do not duplicate their functionality.
2. Implement a local **read-only** device preflight and produce a redacted JSON report.
3. Implement a patch-planner/verifier that can write only to a temporary workspace or feature branch.
4. Add tests proving the agent cannot modify `main`, bypass failed tests, or turn simulated evidence into real evidence.
5. Add a device bridge only after the user identifies the actual device/interface and authorizes a specific connection.
6. Add pool-side verification only through a documented, independently checkable source; keep revenue blocked until payout verification.

No paid hosting, provider activation, pool connection, mining execution, or financial action is enabled by this plan.

## Acceptance criteria

- A simulation fixture can never satisfy real-device or revenue gates.
- The exact candidate commit is linked to every test report.
- A failed test causes rejection and no deployment.
- Every autonomous patch is isolated on a branch and reviewed through a PR.
- Device commands are allowlisted and default to read-only.
- Missing hardware, credentials, tools, or independent evidence results in an explicit blocked state.
- No claim of real mining or income is made without independent evidence.
