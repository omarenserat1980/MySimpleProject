# Windows Server 2025 installation plan — safety boundary

The `windows_server_install_plan.py` command creates a machine-readable **plan only**. It does not download an ISO, provision a disk, format partitions, start a VM, or install Windows.

## Run

```bash
python -m brain_v12.tools.windows_server_install_plan \
  --source-url 'https://go.microsoft.com/fwlink/?linkid=2345730&clcid=0x409&culture=en-us&country=us' \
  --iso-sha256 '<actual-sha256>' \
  --trusted-sha256 '<independently-published-microsoft-sha256>' \
  --iso-size-bytes 6000000000 \
  --disk-size-gib 100 \
  --backend qemu-kvm \
  --backend-available \
  --target-is-virtual-disk \
  --target-unambiguous \
  --authorize-destructive-operations \
  --output artifacts/windows-server-install-plan.json
```

Replace example size and hashes with measured values. A plan is blocked unless the source is HTTPS on a Microsoft domain, a separately trusted checksum matches the observed ISO hash, a compatible backend is available, the disk is explicitly virtual and unambiguous, the disk is at least 64 GiB, and destructive-operation authorization is explicit.

## Partition plan

The plan describes a UEFI/GPT layout: EFI System (260 MiB), Microsoft Reserved (16 MiB), Windows OS (remaining planned space after a 1 GiB recovery reservation), and Windows Recovery (1 GiB). These are planning values, not a command to partition a disk. Actual installation should use supported Windows Setup/DiskPart behavior and revalidate the exact virtual-disk identity immediately before any destructive operation.

## Status semantics

- `BLOCKED`: one or more required preconditions failed.
- `INSTALLATION_PLAN_READY`: preconditions for planning passed only.
- `boot_status=NOT_TESTED`: always emitted by this planner.
- `WINDOWS_FIRST_BOOT_VERIFIED`: never emitted by this planner; requires independent guest-generated evidence from the protected real-boot workflow.

A local SHA-256 computation records file identity but does not authenticate the source. The trusted checksum must be obtained independently from Microsoft or another explicitly trusted publisher channel. Official evaluation media and fully licensed production media have different licensing terms.
