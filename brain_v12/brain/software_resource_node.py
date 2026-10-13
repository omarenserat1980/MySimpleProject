#!/usr/bin/env python3
"""Software-backed CPU/RAM resource node for Brain.

This layer does not fake KVM. It allocates a virtual machine topology backed by
the host's actual CPU/RAM and selects QEMU TCG when /dev/kvm is unavailable.
The resulting guest is still a real VM process; only CPU acceleration is
software emulated.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ResourcePlan:
    host_architecture: str
    host_cpu_count: int
    host_memory_mib: int
    guest_cpu_count: int
    guest_memory_mib: int
    accelerator: str
    kvm_available: bool
    qemu: str | None
    status: str


def host_memory_mib() -> int:
    pages = os.sysconf("SC_PHYS_PAGES")
    page_size = os.sysconf("SC_PAGE_SIZE")
    return (pages * page_size) // (1024 * 1024)


def kvm_available() -> bool:
    return os.path.exists("/dev/kvm") and os.access("/dev/kvm", os.R_OK | os.W_OK)


def build_plan(requested_cpus: int = 2, requested_memory_mib: int = 4096) -> ResourcePlan:
    cpus = max(1, os.cpu_count() or 1)
    mem = max(512, host_memory_mib())
    guest_cpus = max(1, min(requested_cpus, max(1, cpus - 1)))
    guest_mem = max(512, min(requested_memory_mib, max(512, mem // 2)))
    qemu = shutil.which("qemu-system-x86_64")
    kvm = kvm_available()
    accelerator = "kvm" if kvm else "tcg"
    status = "READY" if qemu else "BLOCKED_MISSING_QEMU"
    return ResourcePlan(
        host_architecture=platform.machine(),
        host_cpu_count=cpus,
        host_memory_mib=mem,
        guest_cpu_count=guest_cpus,
        guest_memory_mib=guest_mem,
        accelerator=accelerator,
        kvm_available=kvm,
        qemu=qemu,
        status=status,
    )


def qemu_command(plan: ResourcePlan, iso: str, disk: str, firmware: str | None = None) -> list[str]:
    if plan.status != "READY":
        raise RuntimeError(plan.status)
    cmd = [
        plan.qemu,
        "-machine", "q35",
        "-cpu", "max",
        "-smp", str(plan.guest_cpu_count),
        "-m", str(plan.guest_memory_mib),
        "-drive", f"file={disk},if=virtio,format=qcow2",
        "-cdrom", iso,
        "-boot", "order=d,menu=on",
        "-display", "none",
        "-serial", "stdio",
    ]
    if plan.accelerator == "kvm":
        cmd[1:1] = ["-accel", "kvm"]
    else:
        cmd[1:1] = ["-accel", "tcg,thread=multi"]
    if firmware:
        cmd[1:1] = ["-drive", f"if=pflash,format=raw,readonly=on,file={firmware}"]
    return cmd


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--cpus", type=int, default=2)
    p.add_argument("--memory-mib", type=int, default=4096)
    p.add_argument("--iso")
    p.add_argument("--disk")
    p.add_argument("--firmware")
    p.add_argument("--print-qemu-command", action="store_true")
    args = p.parse_args()
    plan = build_plan(args.cpus, args.memory_mib)
    print(json.dumps(asdict(plan), indent=2, sort_keys=True))
    if args.print_qemu_command:
        if not args.iso or not args.disk:
            p.error("--iso and --disk are required with --print-qemu-command")
        print(json.dumps(qemu_command(plan, args.iso, args.disk, args.firmware)))
    return 0 if plan.status == "READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
