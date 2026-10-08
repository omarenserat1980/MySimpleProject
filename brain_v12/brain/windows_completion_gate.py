from __future__ import annotations
import hashlib, json, time

class WindowsCompletionGate:
    """Independent evidence gate; never treats process exit as Windows boot."""
    REQUIRED={"media","uefi","cpu","guest","network","storage","control"}
    def verify(self, evidence:dict) -> dict:
        reasons=[]
        for key in self.REQUIRED:
            if not evidence.get(key):
                reasons.append("MISSING_"+key.upper())
        guest=evidence.get("guest") or {}
        media=evidence.get("media") or {}
        uefi=evidence.get("uefi") or {}
        cpu=evidence.get("cpu") or {}
        network=evidence.get("network") or {}
        storage=evidence.get("storage") or {}
        control=evidence.get("control") or {}
        if guest.get("os")!="Windows Server 2025": reasons.append("GUEST_OS_NOT_VERIFIED")
        if guest.get("architecture")!="x86_64": reasons.append("GUEST_ARCH_NOT_VERIFIED")
        if not guest.get("boot_verified"): reasons.append("GUEST_BOOT_NOT_VERIFIED")
        if not media.get("sha256"): reasons.append("MEDIA_HASH_MISSING")
        if uefi.get("ready") is not True: reasons.append("UEFI_NOT_VERIFIED")
        if cpu.get("x86_64") is not True: reasons.append("X86_64_CPU_NOT_VERIFIED")
        if network.get("adapter_up") is not True: reasons.append("GUEST_NETWORK_NOT_VERIFIED")
        if network.get("internet_443") is not True: reasons.append("GUEST_INTERNET_NOT_VERIFIED")
        if not storage.get("filesystem"): reasons.append("GUEST_STORAGE_NOT_VERIFIED")
        if int(storage.get("size_bytes") or 0) < 32*1024*1024*1024: reasons.append("GUEST_STORAGE_TOO_SMALL")
        if control.get("schema") != "brain.windows-execution-contract.v1": reasons.append("CONTROL_CONTRACT_SCHEMA_NOT_VERIFIED")
        if control.get("status") != "VERIFIED": reasons.append("CONTROL_CONTRACT_NOT_VERIFIED")
        if control.get("capability") != "windows-server-2025-real-boot": reasons.append("CONTROL_CAPABILITY_NOT_VERIFIED")
        if control.get("executor") != "windows-real-boot-qemu": reasons.append("CONTROL_EXECUTOR_NOT_VERIFIED")
        if not control.get("brain_id"): reasons.append("CONTROL_BRAIN_ID_MISSING")
        if not isinstance(control.get("generation"), int) or control.get("generation") < 1: reasons.append("CONTROL_GENERATION_INVALID")
        if not isinstance(control.get("fencing_token"), int) or control.get("fencing_token") < 1: reasons.append("CONTROL_FENCING_TOKEN_INVALID")
        if not control.get("task_id") or not control.get("attempt_id"): reasons.append("CONTROL_ATTEMPT_IDENTITY_MISSING")
        if evidence.get("boot_source")!="windows-installed-disk":
            reasons.append("BOOT_SOURCE_NOT_INSTALLED_DISK")
        if evidence.get("qemu_status")=="QEMU_EXITED" and not guest.get("boot_verified"):
            reasons.append("QEMU_EXIT_IS_NOT_BOOT_PROOF")
        payload=json.dumps(evidence,sort_keys=True,separators=(",",":")).encode()
        digest=hashlib.sha256(payload).hexdigest()
        result={"status":"WINDOWS_BOOT_VERIFIED" if not reasons else "INCOMPLETE",
                "verified":not reasons,"reasons":reasons,"evidence_sha256":digest,
                "verified_at":time.time()}
        return result
