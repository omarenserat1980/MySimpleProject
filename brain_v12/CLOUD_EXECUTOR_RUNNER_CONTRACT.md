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
