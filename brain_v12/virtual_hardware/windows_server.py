from __future__ import annotations
from dataclasses import dataclass
from .disk import VirtualDisk
from .uefi import VirtualUEFI
from .x86_64 import X86_64CPU
from .os_image import OSImage, windows_server_2025_image

@dataclass
class WindowsServerVM:
    """Brain VM contract for Windows Server 2025.

    The class deliberately separates media validation from OS boot. A Microsoft
    ISO/VHD is never embedded in source control. Full Windows execution requires
    a sufficiently complete x86-64 implementation and device model; this layer
    proves the VM contract and boot prerequisites without faking an OS boot.
    """
    name: str
    ram_bytes: int = 4 * 1024 * 1024 * 1024
    disk_bytes: int = 64 * 1024 * 1024 * 1024
    image: OSImage | None = None

    def __post_init__(self):
        self.cpu=X86_64CPU()
        self.disk=VirtualDisk(self.disk_bytes)
        self.uefi=VirtualUEFI()
        self.powered=False
        self.boot_stage="OFF"
        self.evidence=[]

    def attach_windows_server_2025(self, path=None, sha256=None):
        self.image=windows_server_2025_image(path,sha256)
        return self.image.inspect()

    def boot(self):
        self.evidence=[]
        if self.ram_bytes < 2 * 1024 * 1024 * 1024:
            return self._fail("INSUFFICIENT_RAM")
        if self.disk_bytes < 32 * 1024 * 1024 * 1024:
            return self._fail("INSUFFICIENT_DISK")
        if self.image is None:
            return self._fail("NO_OS_IMAGE")
        media=self.image.inspect()
        self.evidence.append({"stage":"MEDIA","result":media})
        if not media.get("present") or not media.get("verified"):
            return self._fail("OS_MEDIA_NOT_VERIFIED")
        firmware=self.uefi.boot(self.disk,self.image)
        self.evidence.append({"stage":"UEFI","result":firmware})
        if not firmware.get("ok"):
            return self._fail("UEFI_FAILED")
        # Compatibility stub: proves CPU/UEFI handoff, not Windows itself.
        self.cpu.reset()
        stub=[("MOVI","RAX",0x57534F32),("OUT","RAX"),("HLT",)]
        cpu=self.cpu.run(stub)
        self.evidence.append({"stage":"X86_BOOT_STUB","result":cpu})
        self.powered=True
        self.boot_stage="COMPATIBILITY_HANDOFF"
        return self.status()

    def _fail(self, reason):
        self.powered=False
        self.boot_stage="FAILED"
        return {"ok":False,"status":reason,"evidence":list(self.evidence)}

    def status(self):
        return {"ok":self.powered,"name":self.name,"powered":self.powered,
                "boot_stage":self.boot_stage,"ram_bytes":self.ram_bytes,
                "disk_bytes":self.disk_bytes,"image":self.image.inspect() if self.image else None,
                "cpu":{"cycles":self.cpu.cycles,"halted":self.cpu.halted},
                "evidence":list(self.evidence)}
