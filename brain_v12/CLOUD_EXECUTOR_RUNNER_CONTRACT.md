# Brain Cloud Executor Runner Contract

This contract defines the only runner class allowed to execute Windows Real Boot.

## Required GitHub labels

- self-hosted
- linux
- x64
- brain-internal
- qemu
- windows-real-boot
- brain-cloud-executor

## Required runner-provided identity

The runner host/service environment must provide:

- `BRAIN_CLOUD_EXECUTOR=1`
- `BRAIN_CLOUD_EXECUTOR_ID=<stable-or-ephemeral executor identity>`
- `BRAIN_CLOUD_EXECUTOR_ATTESTATION=<host attestation reference>`

These values MUST come from the runner/host environment, not workflow YAML.

**Important security limitation:** the current `cloud_executor_gate.py` only checks that the attestation reference is non-empty. It does not cryptographically validate the reference or prove that an external identity provider issued it. Treat this as a presence check, not cryptographic attestation. Production authorization must remain blocked until signed attestation verification and trust-root configuration are implemented and tested.

## Required substrate

The runner must independently provide:

- x86_64
- `/dev/kvm` readable and writable by the runner
- `qemu-system-x86_64` and `qemu-img`
- working KVM acceleration
- QEMU/OVMF and the Windows workflow toolchain
- writable execution and evidence directories

The bootstrap must check architecture, KVM permissions, required tools, OVMF, and the Cloud Executor Gate **before** downloading/configuring/registering the GitHub runner. A failed preflight must not leave a newly registered runner behind.

## Lifecycle

The preferred production lifecycle is:

`PROVISION -> PREFLIGHT -> REGISTER JIT/EPHEMERAL -> ONE JOB -> PRESERVE EVIDENCE -> DEREGISTER -> DESTROY`

A cloud VM being created or a GitHub runner being online is not capability evidence.

## Gate

`brain_v12/brain/cloud_executor_gate.py` is the substrate gate. It must return `verified=true` before Windows Real Boot can start. This gate proves only the execution substrate; it does not prove Windows booted and, until cryptographic attestation validation is added, does not prove the authenticity of the executor identity.

## Security rules

- Never set Cloud Executor identity in workflow YAML.
- Never print registration tokens, private keys, owner approvals, or other secrets.
- Never create or sign the Windows execution contract inside the workflow.
- Do not start Windows Real Boot unless the separately issued Brain execution contract passes its closed-loop verification gate.
- Preserve evidence and keep the boot result distinct from substrate-gate success.
