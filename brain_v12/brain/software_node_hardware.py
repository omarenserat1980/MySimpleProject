"""Bounded software-only hardware bundle for the initial Brain node.

CPU and RAM use existing BrainVM models; network traffic remains in-memory.
Storage uses the node workspace with a quota. No physical hardware, native
machine-code execution, host networking, or GPU acceleration is provided.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from brain_v12.virtual_hardware.cpu import VirtualCPU
from brain_v12.virtual_hardware.memory import VirtualRAM
from brain_v12.virtual_hardware.network_hardware import VirtualNetworkFabric

SCHEMA = "electronic-brain.software-node-hardware.v1"
DEFAULT_RAM_CELLS = 4096
DEFAULT_STORAGE_QUOTA_BYTES = 64 * 1024 * 1024
MAX_PROGRAM_CYCLES = 10_000


class SoftwareNodeHardware:
    """Composable virtual CPU/RAM/storage/NIC; all resources are explicitly modeled."""

    def __init__(self, root: str | Path, *, ram_cells: int = DEFAULT_RAM_CELLS,
                 storage_quota_bytes: int = DEFAULT_STORAGE_QUOTA_BYTES):
        if ram_cells < 1 or storage_quota_bytes < 1:
            raise ValueError("HARDWARE_CAPACITY_MUST_BE_POSITIVE")
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.storage_quota_bytes = int(storage_quota_bytes)
        self.cpu = VirtualCPU(profile_name="brainvm-baseline")
        self.ram = VirtualRAM(size=int(ram_cells), ecc_enabled=True)
        self.network = VirtualNetworkFabric(packet_trace_limit=64)
        self.network.add_device("brain-node-nic", "nic", ports=1)
        self.network.add_device("brain-node-switch", "switch_l2", ports=2)
        self.network.connect("brain-node-nic", "brain-node-switch", latency_ms_estimate=0.1,
                             bandwidth_mbps_estimate=1000.0)

    def _safe_path(self, relative_path: str) -> Path:
        if not isinstance(relative_path, str) or not relative_path.strip():
            raise ValueError("INVALID_PATH")
        candidate = (self.root / relative_path).resolve()
        if not candidate.is_relative_to(self.root):
            raise ValueError("PATH_OUTSIDE_WORKSPACE")
        return candidate

    def _storage_used_bytes(self) -> int:
        total = 0
        for path in self.root.rglob("*"):
            if path.is_symlink():
                continue
            if path.is_file():
                total += path.stat().st_size
        return total

    def write_text(self, relative_path: str, content: str) -> dict[str, Any]:
        path = self._safe_path(relative_path)
        if not isinstance(content, str):
            raise ValueError("INVALID_CONTENT")
        payload = content.encode("utf-8")
        previous = path.stat().st_size if path.is_file() else 0
        used = self._storage_used_bytes()
        if used - previous + len(payload) > self.storage_quota_bytes:
            raise ValueError("VIRTUAL_STORAGE_QUOTA_EXCEEDED")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return {"path": str(path.relative_to(self.root)), "bytes_written": len(payload),
                "storage_used_bytes": self._storage_used_bytes(),
                "storage_quota_bytes": self.storage_quota_bytes}

    def read_text(self, relative_path: str) -> dict[str, Any]:
        path = self._safe_path(relative_path)
        if not path.is_file():
            raise FileNotFoundError("FILE_NOT_FOUND")
        return {"path": str(path.relative_to(self.root)),
                "content": path.read_text(encoding="utf-8")}

    def run_program(self, program: Any, *, max_cycles: int = MAX_PROGRAM_CYCLES) -> dict[str, Any]:
        if not isinstance(program, list) or not program:
            raise ValueError("BRAINVM_PROGRAM_MUST_BE_NONEMPTY_LIST")
        if not isinstance(max_cycles, int) or not 1 <= max_cycles <= MAX_PROGRAM_CYCLES:
            raise ValueError("BRAINVM_CYCLE_LIMIT_INVALID")
        self.cpu.reset()
        result = self.cpu.run(program, self.ram, max_cycles=max_cycles)
        return {"engine": "BrainVM-1", "native_machine_code": False,
                "result": result, "ram": self.ram.status()}

    def network_self_test(self) -> dict[str, Any]:
        result = self.network.send_packet("brain-node-nic", "brain-node-switch",
                                          protocol="tcp", dst_port=443, size_bytes=64)
        return {**result, "external_network_used": False,
                "physical_nic_used": False, "network_model": "IN_MEMORY_SIMULATION"}

    def status(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "mode": "SOFTWARE_ONLY",
            "physical_hardware_used": False,
            "host_cpu_capacity_claimed": False,
            "host_ram_capacity_claimed": False,
            "native_machine_code_execution": False,
            "cpu": {"model": self.cpu.fidelity_metadata(),
                    "virtual_register_count": len(self.cpu.registers),
                    "execution_isa": "BrainVM-1 tuple ISA"},
            "ram": {**self.ram.status(),
                    "logical_capacity_only": True,
                    "capacity_unit": "addressable_cells"},
            "storage": {"workspace": str(self.root),
                        "quota_bytes": self.storage_quota_bytes,
                        "used_bytes": self._storage_used_bytes(),
                        "quota_enforced": True,
                        "durability": "local_workspace_only"},
            "network": {"model": "IN_MEMORY_SIMULATION",
                        "devices": [d.status() for d in self.network.devices.values()],
                        "links": len(self.network.links),
                        "external_network_used": False,
                        "host_nic_used": False},
            "gpu": {"state": "UNAVAILABLE",
                    "mode": "OPTIONAL_SIMULATED_CAPABILITY_ONLY",
                    "physical_gpu_used": False,
                    "acceleration_claimed": False},
        }
