# Brain Control Plane Contract

## Purpose

Electronic Brain uses one control plane for consequential execution. GitHub Actions is an execution/evidence substrate, not the authority that declares Brain healthy.

## Execution lifecycle

`INTENT -> PLAN -> POLICY -> CAPABILITY -> EXECUTE -> EVIDENCE -> VERIFY -> ACCEPT|REJECT -> MEMORY`

## Rules

1. A task is not successful because a process exited successfully.
2. Every consequential task requires explicit evidence and an independent verification gate.
3. Self-healing must use one active repair plan at a time; no parallel repair loops.
4. Windows Server 2025 real boot is owned by `.github/workflows/brain-windows-real-boot.yml`.
5. Windows success requires the completion gate and boot evidence, including boot from the installed disk.
6. GitHub workflow success alone never proves a Brain capability.
7. Recovery points are created only after verification.
8. Secrets are referenced by name; plaintext secrets are never stored in Brain memory or evidence.
9. Failed tasks retain evidence and diagnosis before any retry.
10. A retry must be bounded and attributable to the preceding failure.

## Capability model

Each capability should declare:

- required executor/device
- required tools
- required permissions
- preflight checks
- success evidence
- independent verification gate
- recovery strategy

## Current Windows capability

Capability: `WINDOWS_REAL_BOOT`

Required executor labels:

`self-hosted, linux, x64, brain-internal, qemu, windows-real-boot`

Verification contract:

`WINDOWS_BOOT_VERIFIED`

Final contract:

`BRAIN_WINDOWS_REAL_BOOT_CONTRACT=VERIFIED`

Until both are evidenced by the workflow artifacts, Windows Server 2025 is considered BLOCKED/UNVERIFIED.

## Queue discipline

The Windows real-boot path must remain single-flight. Do not create parallel Windows boot workflows to compensate for an unverified run.

## Source of truth

Repository state, workflow logs, immutable artifacts, and independent completion gates are evidence. Human-readable status messages are not evidence by themselves.

## Cloud executor capability gate

Windows Real Boot must not start until cloud_executor_gate.py independently verifies the execution substrate: x86_64, usable /dev/kvm, QEMU x86_64, KVM acceleration, and a writable execution surface. The gate is evidence-only and never declares Windows success. The Windows workflow requires this gate as a prerequisite job.

Cloud execution is intended to be ephemeral/JIT. The executor must run one consequential job, preserve required evidence externally, and then be destroyed/cleaned. Provider availability or VM creation alone is not capability evidence.

## Windows execution modes are distinct

Brain must not conflate these two capabilities:

### WINDOWS_CLOUD_NATIVE
A provider-native Windows Server 2025 VM (for example Azure) is provisioned directly by the cloud provider. Infrastructure readiness and a fresh Windows guest heartbeat are required. This proves a cloud Windows runtime, not QEMU ISO installation evidence.

### WINDOWS_REAL_BOOT_QEMU
A Linux x86_64 Cloud Executor runs QEMU/OVMF and boots a Windows Server 2025 ISO into a virtual disk. This requires the independent Cloud Executor Gate, actual KVM/QEMU initialization when KVM mode is selected, Windows boot evidence, and the Windows completion gate. A native Azure Windows VM cannot satisfy this QEMU capability by substitution.

These capabilities have separate evidence contracts and must never share a VERIFIED flag.
