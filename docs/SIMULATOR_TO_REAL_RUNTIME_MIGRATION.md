# Simulator-to-Real Runtime Migration

## Goal

Convert supported Electronic Brain components from simulation-only behavior to real software execution incrementally, without requiring reserved physical hardware and without claiming a live capability from source code alone.

## Inventory tool

Run from the repository root:

```bash
python tools/brain_real_runtime_migration_audit.py
python tools/brain_real_runtime_migration_audit.py --json
python tools/brain_real_runtime_migration_audit.py --json --output artifacts/real-runtime-migration.json
python -m pytest -q tests/test_brain_real_runtime_migration_audit.py
```

The audit is intentionally read-only. It checks that expected source paths exist and reports declared migration states. It does not call external providers, start a server, or promote any component to LIVE.

## Status semantics

- `SIMULATOR_ONLY`: the known path models behavior but does not perform the real operation.
- `INTEGRATION_NOT_IMPLEMENTED`: a required real implementation is missing.
- `IMPLEMENTED_UNVERIFIED`: source exists, but no fresh runtime evidence has been supplied.
- `EXTERNAL_AUTH_REQUIRED`: an external account/credential and an authorized integration test are needed.
- `EXTERNAL_AUTH_AND_COST_GATE_REQUIRED`: provider credentials, explicit cost approval, and resource lifecycle evidence are required.
- `NOT_PROVEN`: no trustworthy end-to-end evidence establishes the real outcome.

None of these statuses means the component is useless; they prevent design/code presence from being confused with real execution.

## Conversion order

1. **Brain core and internal task runtime:** launch the canonical V12 process in an available software runtime; verify health, authenticated API, durable task state, restart recovery, and evidence persistence.
2. **Executor and capability gateway:** route only to a real, online executor that declares the required capability; enforce permission checks, timeouts, isolation, and truthful failure.
3. **Storage and evidence:** persist checkpoints and immutable evidence, then verify hashes and recovery after restart.
4. **Media pipeline:** connect a real renderer, create a non-empty MP4, inspect it with FFprobe, run independent audio/video QC and master QC.
5. **Applications and OS guests:** add explicit native/process/guest adapters one application class at a time. A workflow profile remains simulated until its adapter runs and produces inspectable artifacts.
6. **External integrations:** wire email, source control, payment, publishing, and provider APIs using secrets outside source control; use sandbox/test mode first and verify provider receipts.
7. **Specialized resources:** Azure VMs, Windows Server guests, ASIC/mining, and physical device bridges require separate authorization, provider/device evidence, cost gates, and cleanup/recovery proofs.

## Required evidence for every conversion

Each accepted conversion must record: source commit SHA, capability and adapter ID/version, execution attempt ID, target identity, start/end timestamps, command or request digest (excluding secrets), actual result/artifact digest, independent verification result, and final state. A green workflow unrelated to the target commit is not sufficient.

## Safety boundaries

- No direct writes to `main`; use a feature branch and pull request.
- No paid cloud resources by default. A free-tier or zero-cost entitlement must be verified before provisioning.
- No secrets in source code, artifacts, logs, or committed JSON.
- No autonomous payment, withdrawal, publishing, destructive operation, or OS provisioning without the relevant explicit authority gate.
- Keep simulation available for deterministic tests and failure injection.
- Never convert `SIMULATED` to `LIVE` by renaming a status. A real adapter must run and pass its evidence gates.

## Current scope of this change

This change adds a truthful migration inventory and audit tool. It does not claim that the listed components have already been converted or that external services are live. Conversion is accepted one component at a time only after the listed real acceptance gates pass.
