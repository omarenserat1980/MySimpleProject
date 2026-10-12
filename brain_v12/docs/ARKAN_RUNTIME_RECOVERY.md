# Arkan Runtime Recovery Toolkit

## Termux / Brain runtime diagnostics
Run from the repository checkout:

```bash
bash brain_v12/tools/brain_runtime_diagnostics.sh
```

The read-only report is saved under `~/.brain/recovery-evidence/`. It checks local processes, disk/memory, Brain readiness/media/cinema endpoints, and recent GitHub Actions summaries. Set `GH_TOKEN` in the environment only when needed; do not place tokens in scripts or paste them into reports.

For detailed failed-job logs:

```bash
gh auth login
gh run list --repo omarenserat1980/MySimpleProject --limit 20
gh run view RUN_ID --log-failed
```

## Windows / Hyper-V diagnostics
Copy `brain_v12/tools/arkan_runtime_recovery.ps1` to the Windows Arkan host and run elevated PowerShell in read-only mode:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\arkan_runtime_recovery.ps1
```

It records host memory/disk, Hyper-V service, VM state, attached VHD/ISO paths, runner service/process evidence, and recent Hyper-V events. It does not delete disks, recreate VMs, alter VM memory, or edit firmware.

Only after reviewing the report, a deliberate start can be requested:

```powershell
.\arkan_runtime_recovery.ps1 -StartVM
```

The start guard requires free RAM to exceed VM startup memory plus a 768 MB host reserve. A VM reaching Running is only a power-state observation: verify the guest console and successful Windows login before reporting boot success.

## Indicator rules
- Desktop Commander account known is not the same as a live execution channel.
- TRIGGERcmd with no registered device must be NOT_CONFIGURED / NOT_CONNECTED, never READY.
- A self-hosted runner is eligible only with fresh Online status and matching labels.
- `arkan-virtual-01` is a software-defined identity, not proof a Windows guest is running.
- Windows Server 2025 is BOOT_VERIFIED only after guest boot/login evidence.
- No paid cloud service is required by this toolkit.
