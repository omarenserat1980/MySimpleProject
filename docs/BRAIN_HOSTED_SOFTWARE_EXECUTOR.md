# Brain Hosted Software Executor

## Purpose

This adapter provides a GitHub-hosted replacement for Arkan-dependent **bounded software CI tasks**. It uses the existing allowlisted Brain symbolic executor, reports its identity as `brain-hosted-ci-01`, and runs on an ephemeral `ubuntu-24.04` GitHub-hosted Actions runner.

## What it replaces

- CI-only symbolic CPU smoke tasks and self-tests that do not require a persistent physical machine.
- The need to use the offline Arkan Desktop Commander device for those bounded software checks.

## What it does not replace

- It is not a permanent daemon: GitHub-hosted runners are destroyed after the job.
- Its local SQLite data is job-local, not durable cloud state.
- The task runtime is explicitly `SIMULATED`.
- It does not provision a VM, install Windows, run Hyper-V/QEMU/KVM, or prove Windows Server 2025 boot.
- It is not an authorized runner for the protected `windows-real-boot` workflow.

## Run and verify

```bash
python -m pip install "fastapi>=0.110,<1"
python -m unittest brain_v12.tests.test_hosted_software_executor brain_v12.tests.test_arkan_software_executor -v
python -m brain_v12.brain.hosted_software_executor --task-type cpu_smoke
```

The workflow `.github/workflows/brain-hosted-software-executor.yml` runs these checks and stores sanitized JSON evidence for 30 days. Its assertions require the node ID to be `brain-hosted-ci-01`, runtime mode `EPHEMERAL_CI_JOB`, reality `SIMULATED`, and native Windows boot verification to remain false.

## Arkan retirement policy

1. Use this hosted executor only for the software-only task types above.
2. Keep the real Windows boot gate closed until a designated authorized executor has a real pre-issued contract and the guest emits verifiable boot evidence.
3. Do not delete Arkan-specific source modules or the device registration just because this CI adapter passes: existing APIs/tests may still reference them, and the offline device cannot receive a remote uninstall command.
4. After CI passes and active production references are migrated, retire the old software executor in a separate reviewed change. Physical device revocation/deletion must be performed through the device management service when the device/account owner can authorize it.

## Truthful acceptance criteria

- Hosted software executor tests pass.
- CI evidence identifies an ephemeral hosted runner and labels the task simulated.
- No claim is made that a persistent worker exists.
- No claim is made that Windows Server 2025 booted.
- No cloud resources are provisioned by this workflow.
