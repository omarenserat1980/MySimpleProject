from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class VirtualUEFI:
    """UEFI-like firmware contract for the Brain VM."""
    version: str = "BRAIN-UEFI-1"
    secure_boot: bool = False
    boot_order: list[str] = field(default_factory=lambda: ["disk", "cdrom", "network"])

    def boot(self, disk, optical=None) -> dict:
        evidence = {"firmware": self.version, "secure_boot": self.secure_boot,
                    "boot_order": list(self.boot_order), "devices": []}
        if disk is not None:
            evidence["devices"].append("disk")
        if optical is not None:
            evidence["devices"].append("cdrom")
        if disk is None and optical is None:
            return {**evidence, "ok": False, "status": "NO_BOOT_DEVICE"}
        return {**evidence, "ok": True, "status": "UEFI_READY"}

    def set_boot_order(self, order):
        allowed={"disk","cdrom","network"}
        if not order or any(x not in allowed for x in order):
            raise ValueError("INVALID_BOOT_ORDER")
        self.boot_order=list(order)
        return {"ok":True,"boot_order":list(self.boot_order)}
