from __future__ import annotations
from dataclasses import dataclass
from .cpu import VirtualCPU
from .memory import VirtualRAM
from .bus import VirtualBus
from .devices import VirtualNIC,VirtualStorage,VirtualGPU
from .firmware import VirtualFirmware
from .kernel import VirtualKernel
from .filesystem import VirtualFilesystem
from .bootloader import VirtualBootloader

@dataclass
class VirtualComputer:
    """Software-defined computer: CPU, RAM, bus, firmware, kernel and devices."""
    name: str
    ram_size: int = 65536
    storage_size: int = 1024*1024
    gpu_width: int = 320
    gpu_height: int = 200

    def __post_init__(self):
        self.cpu=VirtualCPU()
        self.ram=VirtualRAM(self.ram_size)
        self.bus=VirtualBus()
        self.storage=VirtualStorage(self.storage_size)
        self.nic=VirtualNIC()
        self.gpu=VirtualGPU(self.gpu_width,self.gpu_height)
        self.firmware=VirtualFirmware()
        self.kernel=VirtualKernel()
        self.filesystem=VirtualFilesystem(self.storage)
        self.bootloader=VirtualBootloader()
        for n,d in [("cpu",self.cpu),("ram",self.ram),("storage",self.storage),("nic",self.nic),("gpu",self.gpu)]:
            self.bus.attach(n,d)
        self.powered=False
        self.boot_count=0
        self.boot_record=None

    def power_on(self):
        self.powered=True
        self.boot_count+=1
        self.cpu.reset()
        self.kernel.reset()
        self.boot_record=self.firmware.boot(self)
        self.boot_record["bootloader"]=self.bootloader.load(self)
        if not self.boot_record["bootloader"].get("ok"):
            self.powered=False
            raise RuntimeError("BOOTLOADER_FAILED")
        if not self.boot_record.get("ok"):
            self.powered=False
            raise RuntimeError("FIRMWARE_BOOT_FAILED")
        return self.status()

    def power_off(self):
        self.powered=False
        return self.status()

    def execute(self,program,max_cycles:int=10000):
        if not self.powered: raise RuntimeError("COMPUTER_POWER_OFF")
        return self.cpu.run(program,self.ram,max_cycles)

    def create_process(self,name):
        if not self.powered: raise RuntimeError("COMPUTER_POWER_OFF")
        return self.kernel.create_process(name)

    def syscall(self,pid,name,**args):
        if not self.powered: raise RuntimeError("COMPUTER_POWER_OFF")
        return self.kernel.syscall(pid,name,**args)

    def status(self):
        return {"name":self.name,"powered":self.powered,"boot_count":self.boot_count,
                "firmware":{"version":self.firmware.VERSION,"booted":bool(self.boot_record and self.boot_record.get("ok"))},
                "bootloader":self.bootloader.VERSION,
                "filesystem":{"files":len(self.storage.files)},
                "kernel":self.kernel.status(),
                "cpu":{"pc":self.cpu.pc,"cycles":self.cpu.cycles,"halted":self.cpu.halted},
                "ram":{"size":self.ram.size},
                "devices":self.bus.device_names(),
                "storage":{"capacity":self.storage.capacity,"files":len(self.storage.files)},
                "network":{"mac":self.nic.mac},"gpu":{"width":self.gpu.width,"height":self.gpu.height}}
