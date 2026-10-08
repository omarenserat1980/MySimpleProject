from __future__ import annotations

"""Host/provider adapters for Resource Fabric.

Adapters only *measure* capacity. They never manufacture it.
"""

import os
import platform
import shutil
import subprocess
from dataclasses import dataclass

from .resource_fabric import ResourceFabric, ResourceKind, ResourceSpec, ResourceState


@dataclass
class HostProbe:
    provider_id: str

    def _cmd(self, *args: str) -> str:
        try:
            return subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL, timeout=5).strip()
        except (OSError, subprocess.SubprocessError):
            return ""

    def probe(self) -> list[ResourceSpec]:
        system = platform.system().lower()
        if system == "windows":
            return self._windows()
        return self._linux()

    def _linux(self) -> list[ResourceSpec]:
        cpu = os.cpu_count() or 1
        mem_kb = 0
        try:
            with open("/proc/meminfo", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        mem_kb = int(line.split()[1])
                        break
        except OSError:
            pass
        memory_gb = max(1, mem_kb // (1024 * 1024))
        specs = [
            ResourceSpec(f"{self.provider_id}:cpu", ResourceKind.COMPUTE, self.provider_id,
                         cpu, "core", {"architecture": platform.machine()}),
            ResourceSpec(f"{self.provider_id}:ram", ResourceKind.MEMORY, self.provider_id,
                         memory_gb, "GB", {"tier": "host"}),
        ]
        disk = shutil.disk_usage("/")
        specs.append(ResourceSpec(f"{self.provider_id}:storage", ResourceKind.STORAGE,
                                  self.provider_id, disk.free // (1024**4), "TB",
                                  {"filesystem": "root", "free_bytes": disk.free}))
        return specs

    def _windows(self) -> list[ResourceSpec]:
        cpu = self._cmd("powershell", "-NoProfile", "-Command",
                        "[Environment]::ProcessorCount")
        mem = self._cmd("powershell", "-NoProfile", "-Command",
                        "[math]::Floor((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory/1GB)")
        disk = self._cmd("powershell", "-NoProfile", "-Command",
                         "[math]::Floor((Get-PSDrive C).Free/1TB)")
        specs = []
        if cpu.isdigit():
            specs.append(ResourceSpec(f"{self.provider_id}:cpu", ResourceKind.COMPUTE,
                                      self.provider_id, int(cpu), "core",
                                      {"architecture": platform.machine()}))
        if mem.isdigit():
            specs.append(ResourceSpec(f"{self.provider_id}:ram", ResourceKind.MEMORY,
                                      self.provider_id, int(mem), "GB", {"tier": "host"}))
        if disk.isdigit():
            specs.append(ResourceSpec(f"{self.provider_id}:storage", ResourceKind.STORAGE,
                                      self.provider_id, int(disk), "TB", {"drive": "C:"}))
        return specs


class HostResourceProvider:
    def __init__(self, fabric: ResourceFabric, provider_id: str | None = None):
        self.fabric = fabric
        self.provider_id = provider_id or os.getenv("BRAIN_PROVIDER_ID") or platform.node() or "host"
        self.probe_engine = HostProbe(self.provider_id)

    def sync(self) -> dict:
        specs = self.probe_engine.probe()
        for spec in specs:
            self.fabric.register(spec)
        return {
            "ok": bool(specs),
            "status": "SYNCED" if specs else "NO_CAPACITY_DETECTED",
            "provider_id": self.provider_id,
            "resource_count": len(specs),
            "resources": [x.public() for x in specs],
            "platform": platform.platform(),
        }

    def inspect(self) -> dict:
        return self.fabric.inspect()
