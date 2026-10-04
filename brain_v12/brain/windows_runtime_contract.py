from __future__ import annotations

"""Brain-native contract for Windows execution."""

from typing import Any, Mapping


class WindowsRuntimeContract:
    name = "BRAIN-WINDOWS-RUNTIME-1"
    target_os = "Windows Server 2025"

    def validate(self, evidence: Mapping[str, Any]) -> tuple[bool, list[str]]:
        reasons: list[str] = []
        guest = evidence.get("guest") or {}
        network = evidence.get("network") or {}
        storage = evidence.get("storage") or {}

        if evidence.get("status") != "WINDOWS_BOOT_VERIFIED":
            reasons.append("WINDOWS_EVIDENCE_STATUS_NOT_VERIFIED")
        if guest.get("os") != self.target_os:
            reasons.append("GUEST_OS_NOT_WINDOWS_SERVER_2025")
        if guest.get("architecture") not in ("AMD64", "x86_64"):
            reasons.append("GUEST_ARCH_NOT_X86_64")
        if guest.get("boot_verified") is not True:
            reasons.append("GUEST_BOOT_NOT_VERIFIED")
        if network.get("adapter_up") is not True:
            reasons.append("NETWORK_ADAPTER_NOT_UP")
        if network.get("internet_443") is not True:
            reasons.append("HTTPS_443_NOT_REACHABLE")
        if not storage.get("filesystem"):
            reasons.append("SYSTEM_FILESYSTEM_MISSING")
        if int(storage.get("size_bytes") or 0) < 32 * 1024 * 1024 * 1024:
            reasons.append("SYSTEM_DISK_BELOW_32GB")
        return (not reasons, reasons)
