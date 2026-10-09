"""Brain Raw Server Composer: staged, software-defined server resource model.

This creates a validated resource manifest. It does NOT manufacture physical RAM/CPU,
provision cloud resources, create a VM, or reserve the reported capacity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.0"


def _available_memory_bytes() -> int:
    """Best-effort available physical memory; returns zero if unknown."""
    if os.name == "nt":
        try:
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MEMORYSTATUSEX()
            status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return int(status.ullAvailPhys)
        except Exception:
            return 0
    try:
        pages = os.sysconf("SC_AVPHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        return int(pages * page_size)
    except (AttributeError, OSError, ValueError):
        return 0


def _total_memory_bytes() -> int:
    if os.name == "nt":
        try:
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MEMORYSTATUSEX()
            status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return int(status.ullTotalPhys)
        except Exception:
            return 0
    try:
        return int(os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE"))
    except (AttributeError, OSError, ValueError):
        return 0


def _disk_info(path: Path) -> dict[str, int]:
    usage = shutil.disk_usage(path)
    return {"total_bytes": int(usage.total), "free_bytes": int(usage.free)}


def _cpu_count() -> int:
    return max(1, int(os.cpu_count() or 1))


def _gpu_probe() -> dict[str, Any]:
    nvidia_smi = shutil.which("nvidia-smi")
    if not nvidia_smi:
        return {"detected": False, "provider": None, "note": "No NVIDIA GPU probe found; GPU capacity is not assumed."}
    try:
        result = subprocess.run(
            [nvidia_smi, "--query-gpu=name,memory.total", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5, check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return {"detected": True, "provider": "NVIDIA", "devices": [line.strip() for line in result.stdout.splitlines() if line.strip()]}
    except (OSError, subprocess.TimeoutExpired):
        pass
    return {"detected": False, "provider": None, "note": "nvidia-smi did not return usable GPU evidence."}


class StageFailure(RuntimeError):
    pass


class RawServerComposer:
    """Build components in dependency order and stop at the first failed gate."""

    ORDER = ["memory_foundation", "ram_pool", "cpu_pool", "storage_pool", "network_profile", "security_baseline", "integration"]

    def __init__(self, output_dir: str | Path, target_ram_gb: float | None = None):
        self.output_dir = Path(output_dir).expanduser().resolve()
        self.target_ram_gb = target_ram_gb
        self.state_dir = self.output_dir / "components"
        self.evidence_dir = self.output_dir / "evidence"
        self.results: dict[str, dict[str, Any]] = {}
        self.started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def _write_json(self, path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _stage(self, name: str, build) -> dict[str, Any]:
        component_path = self.state_dir / f"{name}.json"
        try:
            payload = build()
            payload.update({"component": name, "status": "PASS", "schema_version": SCHEMA_VERSION})
            self._write_json(component_path, payload)
            digest = hashlib.sha256(component_path.read_bytes()).hexdigest()
            record = {"status": "PASS", "path": str(component_path), "sha256": digest}
            self.results[name] = record
            self._write_json(self.evidence_dir / f"{name}.gate.json", record)
            print(f"[PASS] {name} sha256={digest}")
            return payload
        except Exception as exc:
            record = {"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"}
            self.results[name] = record
            self._write_json(self.evidence_dir / f"{name}.gate.json", record)
            print(f"[FAIL] {name}: {record['error']}", file=sys.stderr)
            raise StageFailure(f"Stage {name} failed; later stages were not run.") from exc

    def build(self) -> dict[str, Any]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.evidence_dir.mkdir(parents=True, exist_ok=True)

        memory = self._stage("memory_foundation", self._memory_foundation)
        ram = self._stage("ram_pool", lambda: self._ram_pool(memory))
        cpu = self._stage("cpu_pool", self._cpu_pool)
        storage = self._stage("storage_pool", self._storage_pool)
        network = self._stage("network_profile", self._network_profile)
        security = self._stage("security_baseline", self._security_baseline)
        final = self._stage("integration", lambda: self._integrate(memory, ram, cpu, storage, network, security))
        manifest = {
            "name": "BRAIN-RAW-SERVER",
            "schema_version": SCHEMA_VERSION,
            "created_at": self.started_at,
            "host": {"platform": platform.platform(), "python": platform.python_version(), "hostname": socket.gethostname()},
            "mode": "software-defined-capacity-plan",
            "important_limit": "Logical inventory only. No physical capacity is created or reserved; no cloud/VM is provisioned.",
            "stages": self.results,
            "server": final,
        }
        self._write_json(self.output_dir / "raw_server_manifest.json", manifest)
        raw = (self.output_dir / "raw_server_manifest.json").read_bytes()
        manifest["manifest_sha256"] = hashlib.sha256(raw).hexdigest()
        self._write_json(self.output_dir / "raw_server_manifest.json", manifest)
        self._write_json(self.evidence_dir / "final.gate.json", {
            "status": "PASS", "component_count": len(self.results),
            "failed_components": [k for k, v in self.results.items() if v["status"] != "PASS"],
            "manifest": str(self.output_dir / "raw_server_manifest.json"),
            "manifest_sha256": manifest["manifest_sha256"],
        })
        print(f"[READY] BRAIN-RAW-SERVER manifest={self.output_dir / 'raw_server_manifest.json'}")
        print("[INFO] READY means all local planning gates passed; it does not mean a real server or VM is running.")
        return manifest

    def _memory_foundation(self) -> dict[str, Any]:
        total = _total_memory_bytes()
        available = _available_memory_bytes()
        if total <= 0 or available <= 0:
            raise ValueError("Physical memory telemetry unavailable; cannot pass memory foundation gate.")
        if available > total:
            raise ValueError("Available memory exceeds detected total memory.")
        return {
            "kind": "memory_foundation",
            "host_total_bytes": total,
            "host_available_bytes": available,
            "host_used_bytes": total - available,
            "telemetry_only": True,
            "gate": "PASS",
        }

    def _ram_pool(self, memory: dict[str, Any]) -> dict[str, Any]:
        available = int(memory["host_available_bytes"])
        # Reserve 75% for Windows and other workloads; this is a planning cap, not allocation.
        safe_budget = int(available * 0.25)
        requested = int(self.target_ram_gb * (1024 ** 3)) if self.target_ram_gb is not None else safe_budget
        if requested <= 0:
            raise ValueError("RAM target must be greater than zero.")
        if requested > safe_budget:
            raise ValueError(
                f"Requested logical RAM {requested} bytes exceeds safe planning cap {safe_budget} bytes (25% of currently available host RAM)."
            )
        return {
            "kind": "logical_ram_pool",
            "requested_bytes": requested,
            "requested_gib": round(requested / (1024 ** 3), 3),
            "safe_planning_cap_bytes": safe_budget,
            "allocated": False,
            "reserved": False,
            "gate": "PASS",
            "note": "A capacity plan only; no memory is allocated or reserved.",
        }

    def _cpu_pool(self) -> dict[str, Any]:
        count = _cpu_count()
        return {"kind": "logical_cpu_pool", "host_logical_cpu_count": count, "planned_vcpu_upper_bound": count, "allocated": False, "gate": "PASS"}

    def _storage_pool(self) -> dict[str, Any]:
        info = _disk_info(self.output_dir)
        if info["free_bytes"] < 50 * 1024 * 1024:
            raise ValueError("Less than 50 MiB free on the output volume.")
        return {"kind": "storage_pool", "path": str(self.output_dir), **info, "minimum_free_bytes_gate": 50 * 1024 * 1024, "gate": "PASS"}

    def _network_profile(self) -> dict[str, Any]:
        host = socket.gethostname()
        return {"kind": "network_profile", "hostname": host, "dns_name": None, "public_endpoint_created": False, "ports_opened": False, "gate": "PASS"}

    def _security_baseline(self) -> dict[str, Any]:
        return {
            "kind": "security_baseline",
            "cloud_provisioning": False,
            "automatic_publishing": False,
            "automatic_goal_execution": False,
            "secrets_written_to_disk": False,
            "external_ports_opened": False,
            "gate": "PASS",
        }

    def _integrate(self, memory, ram, cpu, storage, network, security) -> dict[str, Any]:
        components = [memory, ram, cpu, storage, network, security]
        if len(components) != 6 or any(component.get("gate") != "PASS" for component in components):
            raise ValueError("A component did not pass its gate; refusing final composition.")
        return {
            "id": "BRAIN-RAW-SERVER-01",
            "status": "READY_FOR_REVIEW",
            "components": [component["kind"] for component in components],
            "ram_gib_planned": ram["requested_gib"],
            "vcpu_upper_bound": cpu["planned_vcpu_upper_bound"],
            "storage_free_bytes_at_check": storage["free_bytes"],
            "gpu": _gpu_probe(),
            "provisioned": False,
            "health_attestation": "NOT_AVAILABLE_UNTIL_DEPLOYED",
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the Brain Raw Server plan in gated stages.")
    parser.add_argument("--output", default="./brain_raw_server_build", help="Directory for component manifests and evidence.")
    parser.add_argument("--target-ram-gb", type=float, default=None, help="Optional logical RAM target; must fit within 25% of currently available host RAM.")
    args = parser.parse_args(argv)
    if args.target_ram_gb is not None and args.target_ram_gb <= 0:
        parser.error("--target-ram-gb must be greater than zero")
    try:
        RawServerComposer(args.output, args.target_ram_gb).build()
        return 0
    except StageFailure as exc:
        print(f"[BLOCKED] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
