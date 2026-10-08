from __future__ import annotations
import shutil, subprocess
from dataclasses import dataclass

@dataclass
class QemuWindowsBackend:
    """Brain-controlled QEMU backend for a real Windows Server guest."""
    qemu_binary: str = "qemu-system-x86_64"
    memory: str = "4G"
    cpus: int = 2
    machine: str = "q35"
    disk_path: str | None = None
    iso_path: str | None = None

    def available(self) -> bool:
        return shutil.which(self.qemu_binary) is not None

    def command(self, install: bool = True) -> list[str]:
        if not self.disk_path: raise ValueError("DISK_PATH_REQUIRED")
        cmd=[self.qemu_binary,"-machine",self.machine,"-m",self.memory,
             "-smp",str(self.cpus),"-drive",f"file={self.disk_path},format=qcow2,if=virtio",
             "-netdev","user,id=net0","-device","virtio-net-pci,netdev=net0",
             "-display","none","-serial","stdio"]
        if install:
            if not self.iso_path: raise ValueError("ISO_PATH_REQUIRED")
            cmd += ["-cdrom",self.iso_path,"-boot","order=d"]
        return cmd

    def inspect(self) -> dict:
        return {"ok":True,"backend":"qemu-system-x86_64","available":self.available(),
                "binary":shutil.which(self.qemu_binary),"memory":self.memory,
                "cpus":self.cpus,"machine":self.machine,"disk":self.disk_path,"iso":self.iso_path}

    def run(self, install: bool = True, timeout: int = 300) -> dict:
        if not self.available():
            return {"ok":False,"status":"QEMU_NOT_AVAILABLE","inspection":self.inspect()}
        cmd=self.command(install)
        try:
            p=subprocess.run(cmd,text=True,capture_output=True,timeout=timeout,check=False)
        except subprocess.TimeoutExpired as e:
            return {"ok":False,"status":"QEMU_TIMEOUT","stdout":e.stdout or "","stderr":e.stderr or "","command":cmd}
        return {"ok":p.returncode==0,"status":"QEMU_EXITED" if p.returncode==0 else "QEMU_FAILED",
                "returncode":p.returncode,"stdout":p.stdout,"stderr":p.stderr,"command":cmd}
