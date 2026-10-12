# Brain Windows Server 2025 Runbook

## Remote ISO URL path (phone does not store the ISO)

The QEMU executor can fetch official installation media on the remote Linux
executor host. The Android phone does not need to download or store the ISO.
The remote executor still needs enough disk space to cache the media unless its
QEMU build supports an explicitly configured, range-capable remote block
backend; this implementation uses a resumable remote-host cache.

1. Obtain a current direct HTTPS download URL from Microsoft's Evaluation
   Center. Such URLs may expire and must be treated as secrets because they can
   contain temporary signed query parameters.
2. Supply the URL to `QemuWindowsBackend.iso_url` through a protected runtime
   configuration. Never commit the URL or print it in logs.
3. Supply the expected official SHA-256 through `iso_sha256`. The backend
   refuses to fetch media without this value and does not run QEMU unless the
   downloaded file matches it.
4. Set `iso_cache_dir` to a durable path on the remote executor. Partial
   downloads are kept as `.part` files so they can resume when the server
   supports HTTP byte ranges.
5. The fetcher allows HTTPS URLs under `microsoft.com` only, including
   redirects. It does not allow arbitrary hosts.
6. Confirm the executor has enough free disk space for the ISO and a Windows
   virtual disk. This avoids using phone storage but does not eliminate remote
   media storage.
7. Run the QEMU backend only on an authorized Linux x86_64 executor with the
   required QEMU/KVM and UEFI components.

Example configuration in Python (inject the URL and hash at runtime; do not
hardcode secrets):

```python
from brain_v12.virtual_hardware.windows_server_backend import QemuWindowsBackend

backend = QemuWindowsBackend(
    disk_path="/var/lib/brain/windows/WindowsServer2025.qcow2",
    iso_url=windows_iso_url_from_secret_store,
    iso_sha256=verified_windows_iso_sha256,
    iso_cache_dir="/var/cache/brain/windows-media",
)
result = backend.run(install=True, timeout=3600)
```

The helper's successful hash check proves media integrity against the supplied
expected hash; it does not prove that Windows has booted. A valid signed
Microsoft URL and a verified SHA-256 must be supplied by the operator.

## General provisioning and verification

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
