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

The runner service environment must provide:

BRAIN_CLOUD_EXECUTOR=1

This value MUST come from the runner/host environment, not from workflow YAML.

## Required substrate

The runner must independently provide:

- x86_64
- /dev/kvm readable and writable by the runner
- qemu-system-x86_64
- working KVM acceleration
- QEMU/OVMF and the Windows workflow toolchain
- writable work directory

## Lifecycle

The preferred production lifecycle is:

PROVISION -> REGISTER JIT/EPHEMERAL -> ONE JOB -> PRESERVE EVIDENCE -> DEREGISTER -> DESTROY

A cloud VM being created or a GitHub runner being online is not capability evidence.

## Gate

brain_v12/brain/cloud_executor_gate.py is the substrate gate. It must return verified=true before Windows Real Boot can start.

## Security rule

Never set BRAIN_CLOUD_EXECUTOR in workflow YAML. Doing so would allow a non-cloud runner to self-identify as a cloud executor.


## Executor identity and attestation

A production executor must also provide these host/service environment values:

- BRAIN_CLOUD_EXECUTOR=1
- BRAIN_CLOUD_EXECUTOR_ID=<stable-or-ephemeral executor identity>
- BRAIN_CLOUD_EXECUTOR_ATTESTATION_B64=<base64-encoded signed JSON attestation>
- BRAIN_CLOUD_EXECUTOR_ATTESTATION_PUBLIC_KEY_B64=<trusted Ed25519 public key>

The workflow must never set executor identity or attestation. The trusted provisioning
service must sign schema brain.cloud-executor-attestation.v1, binding executor_id,
exact hostname, architecture=x86_64, issued_at, and expires_at. The signature is
Ed25519 over the canonical JSON payload (the six fields named in that schema, sorted
by key with compact separators). The verifier rejects missing trust roots, invalid
signatures, identity mismatches, future-issued/expired attestations, and lifetimes
over 15 minutes. Use an ephemeral one-job runner with a fresh attestation; a long-lived
runner's static attestation will expire and intentionally fail closed. This proves
runner identity/capability only, not that Windows booted.
