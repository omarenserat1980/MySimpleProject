#!/usr/bin/env python3
"""Evidence-aware software CPU/RAM resource planning for Brain.

This plans a QEMU guest from measured host resources. It never claims that a
plan is a running VM, a Windows boot, or physical hardware.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
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
    """Return detected physical memory in MiB, or 0 when detection fails."""
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        if pages <= 0 or page_size <= 0:
            return 0
        return (pages * page_size) // (1024 * 1024)
    except (AttributeError, OSError, ValueError):
        return 0


def kvm_available() -> bool:
    """Report accessible KVM only; never infer it from the OS or QEMU."""
    machine = platform.machine().lower()
    return (
        machine in {"x86_64", "amd64"}
        and os.path.exists("/dev/kvm")
        and os.access("/dev/kvm", os.R_OK | os.W_OK)
    )


def build_plan(requested_cpus: int = 2, requested_memory_mib: int = 4096) -> ResourcePlan:
    if requested_cpus < 1:
        raise ValueError("REQUESTED_CPUS_MUST_BE_POSITIVE")
    if requested_memory_mib < 512:
        raise ValueError("REQUESTED_MEMORY_MUST_BE_AT_LEAST_512_MIB")

    cpus = os.cpu_count() or 0
    mem = host_memory_mib()
    qemu = shutil.which("qemu-system-x86_64")
    kvm = kvm_available()
    accelerator = "kvm" if kvm else "tcg"

    # Leave at least one host CPU available where possible and never invent
    # minimum host RAM. A blocked plan has zero guest allocations.
    if cpus < 2:
        status = "BLOCKED_INSUFFICIENT_HOST_CPU"
        guest_cpus = guest_mem = 0
    elif mem < 1024:
        status = "BLOCKED_INSUFFICIENT_OR_UNKNOWN_HOST_MEMORY"
        guest_cpus = guest_mem = 0
    elif not qemu:
        status = "BLOCKED_MISSING_QEMU"
        guest_cpus = guest_mem = 0
    else:
        guest_cpus = min(requested_cpus, cpus - 1)
        guest_mem = min(requested_memory_mib, mem // 2)
        if guest_mem < 512:
            status = "BLOCKED_INSUFFICIENT_OR_UNKNOWN_HOST_MEMORY"
            guest_cpus = guest_mem = 0
        else:
            status = "PLAN_READY_NOT_EXECUTED"

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
    if plan.status != "PLAN_READY_NOT_EXECUTED" or not plan.qemu:
        raise RuntimeError(plan.status)
    cmd = [
        plan.qemu, "-machine", "q35", "-cpu", "max",
        "-smp", str(plan.guest_cpu_count), "-m", str(plan.guest_memory_mib),
        "-drive", f"file={disk},if=virtio,format=qcow2",
        "-cdrom", iso, "-boot", "order=d,menu=on",
        "-display", "none", "-serial", "stdio",
    ]
    cmd[1:1] = ["-accel", "kvm" if plan.kvm_available else "tcg,thread=multi"]
    if firmware:
        cmd[1:1] = ["-drive", f"if=pflash,format=raw,readonly=on,file={firmware}"]
    return cmd


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cpus", type=int, default=2)
    parser.add_argument("--memory-mib", type=int, default=4096)
    parser.add_argument("--iso")
    parser.add_argument("--disk")
    parser.add_argument("--firmware")
    parser.add_argument("--print-qemu-command", action="store_true")
    args = parser.parse_args()
    try:
        plan = build_plan(args.cpus, args.memory_mib)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(asdict(plan), indent=2, sort_keys=True))
    if args.print_qemu_command:
        if not args.iso or not args.disk:
            parser.error("--iso and --disk are required with --print-qemu-command")
        print(json.dumps(qemu_command(plan, args.iso, args.disk, args.firmware)))
    return 0 if plan.status == "PLAN_READY_NOT_EXECUTED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
