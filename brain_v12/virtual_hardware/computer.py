from __future__ import annotations
from dataclasses import dataclass
from .cpu import VirtualCPU
from .memory import VirtualRAM
from .bus import VirtualBus
from .devices import VirtualNIC,VirtualStorage,VirtualGPU

@dataclass
class VirtualComputer:
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
        for n,d in [("cpu",self.cpu),("ram",self.ram),("storage",self.storage),("nic",self.nic),("gpu",self.gpu)]:
            self.bus.attach(n,d)
        self.powered=False
        self.boot_count=0

    def power_on(self):
        self.powered=True; self.boot_count+=1
        self.cpu.reset()
        return self.status()

    def power_off(self):
        self.powered=False
        return self.status()

    def execute(self,program,max_cycles:int=10000):
        if not self.powered: raise RuntimeError("COMPUTER_POWER_OFF")
        return self.cpu.run(program,self.ram,max_cycles)

    def status(self):
        return {"name":self.name,"powered":self.powered,"boot_count":self.boot_count,
                "cpu":{"pc":self.cpu.pc,"cycles":self.cpu.cycles,"halted":self.cpu.halted},
                "ram":{"size":self.ram.size},
                "devices":self.bus.device_names(),
                "storage":{"capacity":self.storage.capacity,"files":len(self.storage.files)},
                "network":{"mac":self.nic.mac},"gpu":{"width":self.gpu.width,"height":self.gpu.height}}
