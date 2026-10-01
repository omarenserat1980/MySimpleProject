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
