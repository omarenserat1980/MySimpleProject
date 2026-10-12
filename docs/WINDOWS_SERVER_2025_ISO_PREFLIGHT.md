# Windows Server 2025 ISO structural preflight

This is a read-only first gate for the Windows Server 2025 x64 ISO workflow. It records a SHA-256 digest and checks that an ISO can be enumerated by `xorriso` and contains the expected UEFI boot manager, Windows PE setup image, and an installation image.

## Run locally

On Linux with `xorriso` installed:

```bash
python3 brain_v12/tools/windows_server_iso_preflight.py \
  --iso /path/to/official-windows-server-2025.iso \
  --output artifacts/windows-iso-preflight.json
```

Exit code `0` means only `ISO_STRUCTURE_VALIDATED`. Exit code `2` means the media or required tool/files failed the preflight. The source ISO is opened read-only by xorriso and is never changed. The manifest records the source filename, byte size, SHA-256, tool version, and file-structure result.

## Scope and non-claims

- Required paths: `EFI/BOOT/BOOTX64.EFI`, `sources/boot.wim`, and either `sources/install.wim` or `sources/install.esd`.
- This gate does not rebuild, compress, strip, mount for writing, or modify the ISO.
- It does not validate the full WIM payload, signature trust chain, Windows licensing, or driver compatibility.
- It does not prove that UEFI booted, Windows Boot Manager started, Windows Setup appeared, storage was visible, or Windows installed.
- `boot_status` intentionally remains `NOT_TESTED`; only guest-generated evidence accepted by the real-boot completion gate may advance boot status.

## Rebuild policy

Only rebuild a separate copy of official Microsoft media on a compatible Windows environment with supported Microsoft deployment tools (DISM/Oscdimg). Preserve the original ISO and checksum, all UEFI boot entries and boot files, setup/recovery payloads, edition/language/architecture, and Microsoft signing requirements. Do not publish proprietary ISO contents as CI artifacts. Run this preflight on the output ISO, then proceed to the separately protected real-boot workflow. The current BrainVM tuple interpreter is not an x86-64 Windows execution backend; use a compatible x86-64 emulator/virtualization backend such as QEMU with UEFI firmware and an eligible KVM-capable host before attempting a genuine guest boot.

## Status vocabulary

- `NOT_TESTED`: no structural validation evidence.
- `ISO_STRUCTURE_VALIDATED`: required paths and ISO enumeration passed; no boot is implied.
- `FIRMWARE_BOOTED`, `WINDOWS_SETUP_BOOTED`, and `OS_FIRST_BOOT_VERIFIED`: reserved for independent, real execution evidence from the protected boot workflow, never this script.
