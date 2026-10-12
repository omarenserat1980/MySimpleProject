# Brain Windows Runtime

Electronic Brain treats Windows Server 2025 as an execution capability, not as a GitHub Actions feature.

## Architecture

- Brain Runtime decides the task and executor.
- Windows Executor runs the VM or a Windows host.
- GitHub Executor builds, tests, versions and stores evidence when useful.
- Cloud Executor is an independent future execution path.
- Device Executor handles device-specific work.

GitHub is the source of truth for code and evidence history, but Brain must not stop if GitHub Actions is unavailable.

## Success contract

A Windows run is complete only when:

1. Microsoft ISO is valid.
2. install.wim contains Windows Server 2025.
3. unattended media validates.
4. QEMU/OVMF starts.
5. Windows Server 2025 boots from the installed disk.
6. Guest evidence proves OS, architecture, boot, network and storage.
7. WindowsCompletionGate returns WINDOWS_BOOT_VERIFIED.
8. Evidence, hashes and logs are preserved.

A green workflow alone is never success.

## Failure and recovery

Failures remain INCOMPLETE. Brain may:

Detect -> Diagnose -> Repair -> Retry -> Verify -> Complete

Every retry records the attempt, failure class, ISO hash, acceleration mode, logs, guest evidence and completion gate.

## Windows launch strategy

The current GitHub workflow is a verification executor. The Brain-native contract in
brain_v12/brain/windows_runtime_contract.py allows another executor to produce the
same evidence without depending on GitHub Actions.


## Runtime revision

Windows real-boot verification is automatically requested when this runtime contract changes.


## Internal Runner Authority

Windows Server 2025 real boot is a Brain-owned runtime capability. The authoritative
executor is the Brain Internal Runner, not a GitHub-hosted runner.

Required internal labels for the GitHub evidence adapter are:
- `self-hosted`
- `linux`
- `x64`
- `brain-internal`
- `qemu`
- `windows-real-boot`

The Brain execution policy forbids an external executor from becoming a silent
fallback for `windows-server-2025-real-boot`. GitHub remains the source of truth
for committed code, evidence, audit history and verification; it is not the
runtime dependency.

A real internal runner is only considered online after its runner process is
connected and idle and its host preflight proves QEMU/OVMF/xorriso/wimlib and
the required filesystem tools are available. A queued GitHub job is never
treated as proof of runner availability or Windows boot.
