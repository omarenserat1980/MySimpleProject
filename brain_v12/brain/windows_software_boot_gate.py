from __future__ import annotations

import hashlib
import json
import time


class WindowsSoftwareBootGate:
    """Evidence gate for a Windows Server 2025 VM booted with QEMU TCG.

    This gate is deliberately separate from the real-KVM gate. A TCG boot can
    prove that the guest booted under software emulation, but it must never be
    labeled as a KVM/accelerated boot.
    """

    REQUIRED = {"media", "uefi", "cpu", "guest", "storage", "executor"}

    def verify(self, evidence: dict) -> dict:
        reasons = []
        for key in self.REQUIRED:
            if not evidence.get(key):
                reasons.append("MISSING_" + key.upper())

        guest = evidence.get("guest") or {}
        media = evidence.get("media") or {}
        uefi = evidence.get("uefi") or {}
        cpu = evidence.get("cpu") or {}
        storage = evidence.get("storage") or {}
        executor = evidence.get("executor") or {}

        if executor.get("verified") is not True:
            reasons.append("EXECUTOR_NOT_VERIFIED")
        if guest.get("os") != "Windows Server 2025":
            reasons.append("GUEST_OS_NOT_VERIFIED")
        if guest.get("architecture") != "x86_64":
            reasons.append("GUEST_ARCH_NOT_VERIFIED")
        if not guest.get("boot_verified"):
            reasons.append("GUEST_BOOT_NOT_VERIFIED")
        if not media.get("sha256"):
            reasons.append("MEDIA_HASH_MISSING")
        if uefi.get("ready") is not True:
            reasons.append("UEFI_NOT_VERIFIED")
        if cpu.get("x86_64") is not True:
            reasons.append("X86_64_CPU_NOT_VERIFIED")
        if storage.get("filesystem") is None:
            reasons.append("GUEST_STORAGE_NOT_VERIFIED")
        if evidence.get("accelerator") != "tcg":
            reasons.append("SOFTWARE_BOOT_MUST_USE_TCG")
        if evidence.get("kvm_claimed") is True:
            reasons.append("KVM_CLAIM_FORBIDDEN_IN_SOFTWARE_BOOT")
        if evidence.get("boot_source") != "windows-installed-disk":
            reasons.append("BOOT_SOURCE_NOT_INSTALLED_DISK")

        payload = json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()
        digest = hashlib.sha256(payload).hexdigest()
        return {
            "status": "WINDOWS_BOOT_SOFTWARE_EMULATED" if not reasons else "INCOMPLETE",
            "verified": not reasons,
            "reasons": reasons,
            "evidence_sha256": digest,
            "verified_at": time.time(),
        }
