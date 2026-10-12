# Dedicated Windows Boot Proof Tool

## Purpose

`brain_v12/tools/windows_boot_proof.py` has one responsibility: independently decide whether the current run contains sufficient evidence that Windows Server 2025 actually booted from its installed virtual disk.

It is an evidence verifier only. It does not start QEMU, download media, create/modify VMs, mint contracts, change GitHub secrets, change permissions, or execute generated commands.

## Proof requirements

The tool fails closed unless all of the following are true:

- Guest-written evidence uses the expected schema and identifies Windows Server 2025 x86_64 with boot verification.
- The guest marker file contains exactly `WINDOWS_BOOT_VERIFIED`.
- The phase record explicitly identifies `WINDOWS_INSTALLED_AND_BOOTED_FROM_DISK` and `windows-installed-disk`.
- The signed execution contract gate and trusted cloud-executor gate both report verified.
- The evidence is bound to the current GitHub workflow run ID.
- Executor identity and evidence reference match the trusted executor gate.
- The contract fields in combined evidence match the contract gate.
- The existing independent `WindowsCompletionGate` passes every required invariant.

The tool emits sanitized JSON containing a stable SHA-256 digest and reason codes. It never outputs secret values or contract contents.

## Run

After the existing real-boot workflow has collected its evidence:

```bash
python3 brain_v12/tools/windows_boot_proof.py \
  --evidence windows-combined-evidence.json \
  --marker /tmp/windows-boot-marker \
  --phase windows-boot-phase.txt \
  --contract-gate windows-execution-contract-gate.json \
  --executor-gate cloud-executor-gate.json \
  --run-id "$GITHUB_RUN_ID" \
  --output windows-boot-proof.json
```

Exit code `0` means the evidence passed. Exit code `2` means the evidence is incomplete or invalid. A successful process launch, QEMU start, green CI run, or file existence by itself is not boot proof.

## Permissions

Keep the workflow permission set minimal (`contents: read`) and retain the existing protected environment, signed contract, trusted executor, and runner gates. Do not grant repository administration, secret-write, or unrestricted host privileges to an evidence verifier. The actual boot workflow must use only its separately authorized, least-privilege runtime capabilities.

## Scope boundary

This tool proves evidence for one workflow run; it does not provision infrastructure or claim that a boot occurred when evidence is missing. The existing Windows completion gate remains authoritative and is invoked as part of verification.
