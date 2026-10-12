# Windows Server 2025 ISO structural preflight and safe rebuild

This first gate records a SHA-256 digest and checks that an ISO can be enumerated by xorriso and contains the expected UEFI boot manager, Windows PE setup image, and an installation image.

## Structural preflight on Linux

```bash
python3 brain_v12/tools/windows_server_iso_preflight.py \
  --iso /path/to/official-windows-server-2025.iso \
  --output artifacts/windows-iso-preflight.json
```

Exit code 0 means only ISO_STRUCTURE_VALIDATED. Exit code 2 means the media or required tool/files failed the preflight. The source ISO is never changed.

## Rebuild a separate ISO on Windows

Use official Microsoft media and a compatible Windows machine with the Windows ADK oscdimg.exe. Example PowerShell command:

```powershell
.\brain_v12\tools\rebuild_windows_server_iso.ps1 -SourceIso 'D:\ISO\WindowsServer2025.iso' -OutputIso 'D:\ISO-Output\WindowsServer2025-rebuilt.iso' -Workspace 'D:\ISO-Work\run-001' -OscdimgPath 'C:\Program Files (x86)\Windows Kits\10\Assessment and Deployment Kit\Deployment Tools\amd64\Oscdimg\oscdimg.exe'
```

The script refuses to overwrite the source or an existing output, requires a fresh workspace, mounts the source read-only, copies rather than edits the media, checks UEFI/Setup/install image files and boot-image inputs, calls Oscdimg with explicit BIOS and UEFI boot entries, and writes a JSON manifest plus build logs. It does not compress or strip Windows images. If source media lacks required boot-image inputs, the script stops rather than guessing a boot layout.

## Scope and non-claims

- Required files include EFI/BOOT/BOOTX64.EFI, sources/boot.wim, and either sources/install.wim or sources/install.esd.
- Structural validation and ISO rebuild do not prove firmware boot, Windows Boot Manager startup, Setup visibility, storage detection, or OS installation.
- The Linux preflight does not validate the full WIM payload, signature trust chain, licensing, or driver compatibility.
- Do not publish proprietary ISO contents as CI artifacts.
- The BrainVM tuple interpreter is not an x86-64 Windows execution backend. A genuine guest boot requires a compatible x86-64 emulator/virtualization backend, UEFI firmware, and a capable host. The protected real-boot workflow must independently collect guest-generated evidence.

## Status vocabulary

- NOT_TESTED: no structural validation evidence.
- ISO_STRUCTURE_VALIDATED: required paths and ISO enumeration passed; no boot is implied.
- REBUILT_STRUCTURE_VALIDATED_NOT_BOOT_TESTED: a separate ISO was generated, hashed, remounted read-only, and checked for required boot/setup files; no firmware boot is implied.
- REBUILT_NOT_BOOT_TESTED: legacy status used by earlier script versions; it does not imply structural validation of the generated output.
- FIRMWARE_BOOTED, WINDOWS_SETUP_BOOTED, and OS_FIRST_BOOT_VERIFIED are reserved for independent, real execution evidence from the protected boot workflow.
