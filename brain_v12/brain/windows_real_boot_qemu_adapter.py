"""Brain-owned Windows Server 2025 QEMU runtime adapter.

Authority is verified before process creation. The adapter supports both a
blocking run and a supervised start so the caller can collect guest evidence
while QEMU is alive.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import subprocess
from .internal_runner import InternalRunner
from .windows_real_boot_closed_loop_gate import load_and_verify

CAPABILITY="windows-server-2025-real-boot"
EXECUTOR="windows-real-boot-qemu"

@dataclass(frozen=True)
class QemuRunResult:
    ok: bool
    returncode: int
    pid: int|None
    command: tuple[str,...]
    contract_sha256: str

class WindowsRealBootQemuAdapter:
    def __init__(self, runner:InternalRunner|None=None)->None:
        self.runner=runner or InternalRunner()

    def authorize(self, contract_path:str|None=None)->dict:
        evidence=load_and_verify(contract_path)
        c=evidence["contract"]
        if c.get("capability")!=CAPABILITY:
            raise RuntimeError("WINDOWS_QEMU_ADAPTER_CAPABILITY_INVALID")
        if c.get("executor")!=EXECUTOR:
            raise RuntimeError("WINDOWS_QEMU_ADAPTER_EXECUTOR_INVALID")
        self.runner.require("qemu")
        return evidence

    def build_command(self, *, os_disk:str,evidence_disk:str,proof_iso:str,ovmf_vars:str,
                      qmp_socket:str="qmp.sock",serial_log:str="qemu-serial.log",
                      memory:str="2G",smp:int=2)->list[str]:
        code="/usr/share/OVMF/OVMF_CODE_4M.fd"
        missing=[p for p in (os_disk,evidence_disk,proof_iso,ovmf_vars,code) if not Path(p).exists()]
        if missing: raise RuntimeError("WINDOWS_QEMU_RUNTIME_INPUT_MISSING:"+",".join(missing))
        # Each argv element must be a separate, unpadded option. A leading
        # space before "-machine" makes QEMU reject the option before boot.
        command = [
            "qemu-system-x86_64", "-machine", "q35,accel=kvm", "-cpu", "max",
            "-m", memory, "-smp", str(smp),
            "-drive", f"if=pflash,format=raw,readonly=on,file={code}",
            "-drive", f"if=pflash,format=raw,file={ovmf_vars}",
            "-device", "ich9-ahci,id=sata",
            "-drive", f"file={os_disk},format=qcow2,if=none,id=osdisk",
            "-device", "ide-hd,bus=sata.2,drive=osdisk",
            "-drive", f"file={evidence_disk},format=raw,if=none,id=evidence",
            "-device", "ide-hd,bus=sata.3,drive=evidence",
            "-nic", "user,model=e1000",
            "-drive", f"file={proof_iso},media=cdrom,if=none,id=installmedia,readonly=on",
            "-device", "ide-cd,bus=sata.1,drive=installmedia",
            "-boot", "once=d,menu=off", "-display", "none",
            "-qmp", f"unix:{qmp_socket},server=on,wait=off",
            "-serial", f"file:{serial_log}",
        ]
        if any(arg != arg.strip() for arg in command):
            raise RuntimeError("WINDOWS_QEMU_ARGUMENT_WHITESPACE_INVALID")
        return command

    def start(self, *,os_disk:str,evidence_disk:str,proof_iso:str,ovmf_vars:str,
              contract_path:str|None=None,cwd:str|None=None,**kwargs)->tuple[subprocess.Popen,dict]:
        evidence=self.authorize(contract_path)
        command=self.build_command(os_disk=os_disk,evidence_disk=evidence_disk,proof_iso=proof_iso,
                                   ovmf_vars=ovmf_vars,**kwargs)
        work=Path(cwd or ".")
        log=(work/"qemu-console.log").open("ab")
        try:
            proc=subprocess.Popen(command,cwd=cwd,stdout=log,stderr=subprocess.STDOUT)
        except Exception:
            log.close()
            raise
        return proc,{"verified":True,"contract_sha256":evidence["contract_sha256"],"pid":proc.pid,"command":command}

    def run(self, *,os_disk:str,evidence_disk:str,proof_iso:str,ovmf_vars:str,
            contract_path:str|None=None,cwd:str|None=None,timeout:int=3600,**kwargs)->QemuRunResult:
        proc,meta=self.start(os_disk=os_disk,evidence_disk=evidence_disk,proof_iso=proof_iso,
                             ovmf_vars=ovmf_vars,contract_path=contract_path,cwd=cwd,**kwargs)
        try: rc=proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill(); rc=proc.wait()
        return QemuRunResult(rc==0,rc,proc.pid,tuple(meta["command"]),meta["contract_sha256"])

def main()->int:
    import argparse
    p=argparse.ArgumentParser()
    for n in ("os-disk","evidence-disk","proof-iso","ovmf-vars"): p.add_argument("--"+n,required=True)
    p.add_argument("--contract");p.add_argument("--cwd");p.add_argument("--timeout",type=int,default=3600)
    a=p.parse_args()
    r=WindowsRealBootQemuAdapter().run(contract_path=a.contract,os_disk=a.os_disk,evidence_disk=a.evidence_disk,
                                       proof_iso=a.proof_iso,ovmf_vars=a.ovmf_vars,cwd=a.cwd,timeout=a.timeout)
    print({"ok":r.ok,"returncode":r.returncode,"contract_sha256":r.contract_sha256})
    return 0 if r.ok else r.returncode or 1

if __name__=="__main__": raise SystemExit(main())
