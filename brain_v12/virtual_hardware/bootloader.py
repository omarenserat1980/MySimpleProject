from __future__ import annotations

class VirtualBootloader:
    """Loads a deterministic kernel image from the virtual filesystem."""
    VERSION="BRAIN-BOOT-1"
    KERNEL_PATH="/boot/kernel.bin"

    def load(self,computer):
        if not computer.filesystem.exists(self.KERNEL_PATH):
            return {"ok":True,"status":"KERNEL_OPTIONAL","bootloader":self.VERSION}
        image=computer.filesystem.read(self.KERNEL_PATH)
        if not image:
            return {"ok":False,"status":"KERNEL_EMPTY","bootloader":self.VERSION}
        return {"ok":True,"status":"KERNEL_LOADED","bootloader":self.VERSION,"bytes":len(image)}

    def boot_ready(self, computer, evidence):
        """Return BRAIN_READY only after the self-trust gate passes."""
        loaded = self.load(computer)
        if not loaded.get("ok"):
            return {**loaded, "status":"BRAIN_BOOT_BLOCKED", "ready":False}
        if not evidence or not evidence.get("ok"):
            return {
                **loaded,
                "status":"BRAIN_BOOT_BLOCKED",
                "ready":False,
                "failed_checks": list((evidence or {}).get("failed_checks", ())),
            }
        return {**loaded, "status":"BRAIN_READY", "ready":True,
                "gate":evidence.get("gate","BRAIN-SELF-TRUST-GATE-1")}
