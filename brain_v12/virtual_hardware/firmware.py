from __future__ import annotations

class VirtualFirmware:
    """Deterministic BIOS-like firmware for the Brain virtual computer."""
    VERSION="BRAIN-BIOS-1"

    def __init__(self):
        self.boot_log=[]

    def boot(self, computer):
        self.boot_log=[]
        self.boot_log.append("POWER_ON")
        self.boot_log.append("MEMORY_OK" if computer.ram.size>0 else "MEMORY_FAIL")
        self.boot_log.append("CPU_OK")
        self.boot_log.append("DEVICES:"+",".join(computer.bus.device_names()))
        self.boot_log.append("BOOT_OK")
        return {"ok":True,"firmware":self.VERSION,"boot_log":list(self.boot_log)}
