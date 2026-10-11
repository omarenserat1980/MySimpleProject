# Golden Loop Closure Auditor

## Purpose

The Golden Closed Loop implementation already orchestrates intent, authorization,
execution, observation, independent verification, commit, learning, recovery,
and evidence recording. This auditor adds a final, deterministic readiness gate
for the **real production closure**. It explicitly distinguishes a simulated
Arkan twin from a real Windows Server 2025 guest boot.

## Usage

A trusted probe/collector must create an evidence snapshot JSON file. The
snapshot is evidence input, not an authorization source. Example:

```bash
python -m brain_v12.brain.golden_loop_closure_auditor golden-loop-evidence.json --output golden-loop-audit.json
```

Exit code `0` means every required proof obligation is present; exit code `2`
means blocked. Missing values, strings that merely look like booleans, source
commit mismatches, missing runner labels, and simulated guest evidence all fail
closed. The report lists exact blocker codes.

## Required evidence families

- **Repository/CI:** full source commit SHA, commit-bound evidence, required CI checks passing.
- **Runner:** `BRAIN_RUNNER_WATCH_TOKEN` configured (value never included), runner API read succeeds, required self-hosted Linux x64 labels are present, runner online, execution and runtime probes pass.
- **Execution contract:** issued by Brain Control Plane, cryptographic signature verified, commit binding, valid lease/fencing, unexpired, requested capability authorized.
- **Executor:** cryptographic attestation, same designated runner for boot and attestation, QEMU/KVM capability.
- **Windows:** ISO validated, installed-disk boot proven, guest identity and health verified, evidence explicitly tagged `REAL`.
- **Evidence/recovery:** hashes verified, independent verification, persistence across restart, restart recovery, idempotency and rollback tested.
- **Governance:** scoped owner approval, cost gate, emergency stop test.

## Current known blockers

See [Issue #343](https://github.com/omarenserat1980/MySimpleProject/issues/343) for the runner watcher 403 / missing
`BRAIN_RUNNER_WATCH_TOKEN`, and [Issue #225](https://github.com/omarenserat1980/MySimpleProject/issues/225)
for the missing pre-issued Control Plane execution contract. These are separate
gates. The auditor cannot create the token, mint a contract, start an offline
runner, or provision paid infrastructure.

## Trust model

The auditor verifies the supplied shape and exact values; it does not itself
authenticate the producer of each snapshot field. Production integration must
feed it records from trusted probes, verify their signatures and freshness, and
retain the original evidence. A manually authored all-true JSON file is not
production proof and must never be used to claim that the loop has closed.
