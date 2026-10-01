from __future__ import annotations
import hashlib, json, os, time

class WindowsCompletionGate:
    """Independent evidence gate; never treats process exit as Windows boot."""
    REQUIRED={"media","uefi","cpu","guest","network","storage"}
    def verify(self, evidence:dict) -> dict:
        reasons=[]
        for key in self.REQUIRED:
            if not evidence.get(key):
                reasons.append("MISSING_"+key.upper())
        guest=evidence.get("guest") or {}
        if guest.get("os")!="Windows Server 2025": reasons.append("GUEST_OS_NOT_VERIFIED")
        if guest.get("architecture")!="x86_64": reasons.append("GUEST_ARCH_NOT_VERIFIED")
        if evidence.get("qemu_status")=="QEMU_EXITED" and not guest.get("boot_verified"):
            reasons.append("QEMU_EXIT_IS_NOT_BOOT_PROOF")
        payload=json.dumps(evidence,sort_keys=True,separators=(",",":")).encode()
        digest=hashlib.sha256(payload).hexdigest()
        result={"status":"WINDOWS_BOOT_VERIFIED" if not reasons else "INCOMPLETE",
                "verified":not reasons,"reasons":reasons,"evidence_sha256":digest,
                "verified_at":time.time()}
        return result
