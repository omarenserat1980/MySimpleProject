"""Brain-owned Windows Server 2025 QEMU runtime adapter.

The adapter is intentionally small: it owns the runtime boundary, while the
existing contract gate owns authority verification and the completion gate owns
guest verification. No workflow may self-authorize through this adapter.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
from typing import Sequence

from .internal_runner import InternalRunner
from .windows_real_boot_closed_loop_gate import load_and_verify

CAPABILITY = "windows-server-2025-real-boot"
EXECUTOR = "windows-real-boot-qemu"


@dataclass(frozen=True)
class QemuRunResult:
    ok: bool
    returncode: int
    pid: int | None
    command: tuple[str, ...]
    contract_sha256: str


class WindowsRealBootQemuAdapter:
    """Single Brain-owned execution boundary for the Windows QEMU guest."""

    def __init__(self, runner: InternalRunner | None = None) -> None:
        self.runner = runner or InternalRunner()

    def authorize(self, *, contract_path: str | None = None) -> dict:
        evidence = load_and_verify(contract_path)
        contract = evidence["contract"]
        if contract.get("capability") != CAPABILITY:
            raise RuntimeError("WINDOWS_QEMU_ADAPTER_CAPABILITY_INVALID")
        if contract.get("executor") != EXECUTOR:
            raise RuntimeError("WINDOWS_QEMU_ADAPTER_EXECUTOR_INVALID")
        self.runner.require("qemu")
        return evidence

    def build_command(
        self,
        *,
        os_disk: str,
        evidence_disk: str,
        proof_iso: str,
        ovmf_vars: str,
        qmp_socket: str = "qmp.sock",
        serial_log: str = "qemu-serial.log",
        console_log: str = "qemu-console.log",
        memory: str = "4G",
        smp: int = 2,
    ) -> list[str]:
        code = "/usr/share/OVMF/OVMF_CODE_4M.fd"
        required = [os_disk, evidence_disk, proof_iso, ovmf_vars, code]
        missing = [p for p in required if not Path(p).exists()]
        if missing:
            raise RuntimeError("WINDOWS_QEMU_RUNTIME_INPUT_MISSING:" + ",".join(missing))
        return [
            "qemu-system-x86_64",
            "-machine", "q35,accel=kvm:tcg",
            "-cpu", "max",
            "-m", memory,
            "-smp", str(smp),
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
            "-boot", "once=d,menu=off",
            "-display", "none",
            "-qmp", f"unix:{qmp_socket},server=on,wait=off",
            "-serial", f"file:{serial_log}",
        ]

    def run(
        self,
        *,
        os_disk: str,
        evidence_disk: str,
        proof_iso: str,
        ovmf_vars: str,
        contract_path: str | None = None,
        cwd: str | None = None,
        timeout: int = 3600,
        **kwargs,
    ) -> QemuRunResult:
        evidence = self.authorize(contract_path=contract_path)
        command = self.build_command(
            os_disk=os_disk,
            evidence_disk=evidence_disk,
            proof_iso=proof_iso,
            ovmf_vars=ovmf_vars,
            **kwargs,
        )
        console = Path(cwd or ".") / str(kwargs.get("console_log", "qemu-console.log"))
        with console.open("ab") as log:
            completed = subprocess.run(
                command,
                cwd=cwd,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=timeout,
                check=False,
            )
        return QemuRunResult(
            ok=completed.returncode == 0,
            returncode=completed.returncode,
            pid=None,
            command=tuple(command),
            contract_sha256=evidence["contract_sha256"],
        )


def main() -> int:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--contract")
    p.add_argument("--os-disk", required=True)
    p.add_argument("--evidence-disk", required=True)
    p.add_argument("--proof-iso", required=True)
    p.add_argument("--ovmf-vars", required=True)
    p.add_argument("--cwd")
    p.add_argument("--timeout", type=int, default=3600)
    a = p.parse_args()
    result = WindowsRealBootQemuAdapter().run(
        contract_path=a.contract,
        os_disk=a.os_disk,
        evidence_disk=a.evidence_disk,
        proof_iso=a.proof_iso,
        ovmf_vars=a.ovmf_vars,
        cwd=a.cwd,
        timeout=a.timeout,
    )
    print({"ok": result.ok, "returncode": result.returncode,
           "contract_sha256": result.contract_sha256})
    return 0 if result.ok else result.returncode or 1


if __name__ == "__main__":
    raise SystemExit(main())
