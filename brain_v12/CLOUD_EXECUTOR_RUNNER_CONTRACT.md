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
- `BRAIN_CLOUD_EXECUTOR_ATTESTATION_FILE=<path to signed JSON attestation>`
- `BRAIN_CLOUD_EXECUTOR_ATTESTATION_PUBLIC_KEY_B64=<trusted Ed25519 public key>`

The attestation file and trust anchor must be provisioned out of band by the trusted Brain/control-plane issuer. Never generate the production signing key in GitHub Actions or on the executor. Never place the private key on the runner.

The verifier requires schema `brain.cloud-executor-attestation.v1`, a matching executor ID, audience `brain-cloud-executor`, a nonce, issue/expiry times with a maximum one-hour validity, and a valid Ed25519 signature over the canonical document fields. The public key must be provisioned through a trusted host-management channel; an environment variable alone is not a trust-root distribution strategy.

## Required substrate

The runner must independently provide:

- x86_64
- `/dev/kvm` readable and writable by the runner
- `qemu-system-x86_64` and `qemu-img`
- working KVM acceleration
- QEMU/OVMF and the Windows workflow toolchain
- writable execution and evidence directories

The bootstrap checks architecture, KVM permissions, required tools, OVMF, and the signed-attestation Cloud Executor Gate **before** downloading/configuring/registering the GitHub runner. A failed preflight must not leave a newly registered runner behind.

## Lifecycle

The preferred production lifecycle is:

`PROVISION -> SIGNED ATTESTATION -> PREFLIGHT -> REGISTER JIT/EPHEMERAL -> ONE JOB -> PRESERVE EVIDENCE -> DEREGISTER -> DESTROY`

A cloud VM being created or a GitHub runner being online is not capability evidence. The signed attestation establishes only the executor identity claims covered by the trusted issuer; it does not prove Windows booted.

## Gate

`brain_v12/brain/cloud_executor_gate.py` must return `verified=true` before Windows Real Boot can start. The gate combines signed identity validation with x86_64, KVM, QEMU, and writable-surface checks. It is not a Windows boot completion gate.

## Security rules

- Never set Cloud Executor identity in workflow YAML.
- Never print registration tokens, private keys, owner approvals, or attestation contents.
- Never create or sign the Windows execution contract inside the workflow.
- Do not start Windows Real Boot unless the separately issued Brain execution contract passes its closed-loop verification gate.
- Preserve evidence and keep boot completion distinct from substrate-gate success.
