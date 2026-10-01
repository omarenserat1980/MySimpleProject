# Brain Windows Server 2025 Runbook

1. Obtain official Windows Server 2025 evaluation media from Microsoft. Keep ISO/VHD outside Git.
2. Register media in Brain with path and SHA-256; unverified media is rejected.
3. Provision a Blade Server and create a Windows Server 2025 VM.
4. Select an execution backend:
   - Brain x86-64 compatibility interpreter for deterministic tests.
   - QEMU x86-64 for real guest execution when available.
   - Otherwise remain BLOCKED.
5. Boot the official ISO and install Windows to the virtual disk.
6. Verify the guest independently: Windows Server 2025, x64, disk, network, and persistent evidence.
7. QEMU process exit alone is never WINDOWS_BOOT_VERIFIED.
8. Production use requires the applicable Microsoft licensing rights.
