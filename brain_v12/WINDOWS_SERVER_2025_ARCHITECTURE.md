# Brain Windows Server 2025 Virtualization Architecture

## Contract

Brain owns the virtual-machine control plane. Microsoft media remains external and is referenced by path plus SHA-256; it is never committed to Git.

Pipeline:

`OS media -> integrity verification -> virtual disk -> Virtual UEFI -> x86-64 CPU -> boot handoff -> OS runtime -> network/storage -> verification`

## Current implementation

- Sparse `VirtualDisk` prevents allocating a full 32+ GiB disk in RAM.
- `VirtualUEFI` defines a deterministic firmware/boot-order boundary.
- `X86_64CPU` is a deliberately small interpreter subset, not a complete x86-64 emulator.
- `OSImage` records media metadata and verifies a supplied SHA-256.
- `WindowsServerVM` enforces resource/media gates and records boot evidence.

## Windows Server 2025 requirements

Microsoft documents Windows Server 2025 as requiring an x64-compatible processor and a minimum 2 GB RAM for the listed installation modes, with 32 GB as an absolute minimum system-partition size. Microsoft also documents additional CPU capabilities and networking requirements. Brain therefore does not claim that the current toy CPU can run Windows Server itself.

Official evaluation media is available from Microsoft's Evaluation Center as 64-bit ISO and VHD; the evaluation expires after 180 days.

## Gates

1. MEDIA_PRESENT
2. MEDIA_SHA256_VERIFIED
3. DISK_GEOMETRY_VALID
4. UEFI_READY
5. X86_64_BOOT_HANDOFF
6. WINDOWS_BOOT_VERIFIED
7. NETWORK_VERIFIED
8. STORAGE_VERIFIED
9. FINAL_VM_QC

Stages 1-5 are implemented as testable contracts. Stage 6 is intentionally blocked until a real Windows-capable x86-64 emulation/virtualization backend exists and actual boot evidence is captured.

## Next engineering layers

1. Expand x86-64 decoder/register/memory model.
2. Add PCIe, NVMe/virtio-like storage and Ethernet devices.
3. Add ACPI/SMBIOS/TPM/Secure Boot models as required by the target guest.
4. Add executable PE/UEFI loading and interrupt/exception handling.
5. Add Windows installation state machine and virtual console.
6. Run a real Windows Server 2025 guest and collect independent evidence.

No stage may report `WINDOWS_BOOT_VERIFIED` from a simulation.
