"""Device-backed Cloud Pool for Electronic Brain.

The pool treats user-owned devices as cloud nodes managed by Brain. It does not
create virtual CPU/RAM, provision external cloud resources, or execute tasks.
It only measures/observes bounded capacity and feeds the existing policy
orchestrator.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import os
import platform
import shutil
import socket
from typing import Any

from .portable_resource_orchestrator import (
    ExecutorCapacity,
    LocalResourceBudget,
    PortableResourceOrchestrator,
    ResourceDemand,
    ScheduleDecision,
    ScheduleRequest,
)


@dataclass(frozen=True)
class CloudNode:
    node_id: str
    role: str
    platform: str
    online: bool
    healthy: bool
    cpu_cores: float
    memory_mb: int
    disk_mb: int
    source: str
    observed: bool
    capabilities: tuple[str, ...] = ()
    metadata: dict[str, Any] | None = None

    def public(self) -> dict[str, Any]:
        return asdict(self)


def _memory_mb() -> int:
    """Best-effort physical-memory measurement without third-party packages."""
    try:
        if os.name == "nt":
            import ctypes

            class MemoryStatus(ctypes.Structure):
                _fields_ = [
                    ("length", ctypes.c_ulong),
                    ("memory_load", ctypes.c_ulong),
                    ("total_phys", ctypes.c_ulonglong),
                    ("avail_phys", ctypes.c_ulonglong),
                    ("total_page", ctypes.c_ulonglong),
                    ("avail_page", ctypes.c_ulonglong),
                    ("total_virtual", ctypes.c_ulonglong),
                    ("avail_virtual", ctypes.c_ulonglong),
                    ("avail_extended", ctypes.c_ulonglong),
                ]

            status = MemoryStatus()
            status.length = ctypes.sizeof(MemoryStatus)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return int(status.total_phys / 1024 / 1024)
        meminfo = "/proc/meminfo"
        if os.path.exists(meminfo):
            with open(meminfo, encoding="utf-8") as handle:
                for line in handle:
                    if line.startswith("MemTotal:"):
                        return int(line.split()[1]) // 1024
    except (OSError, ValueError, AttributeError):
        pass
    return 0


def local_host_node(*, node_id: str | None = None) -> CloudNode:
    """Measure the host running Brain; zero means measurement unavailable."""
    root = os.path.abspath(os.getenv("BRAIN_CLOUD_DISK_ROOT", os.getcwd()))
    try:
        disk_mb = int(shutil.disk_usage(root).free / 1024 / 1024)
    except OSError:
        disk_mb = 0
    cpu = float(max(0, os.cpu_count() or 0))
    memory = _memory_mb()
    return CloudNode(
        node_id=(node_id or os.getenv("BRAIN_CLOUD_HOST_ID") or socket.gethostname()),
        role="compute_host",
        platform=platform.system().lower() or "unknown",
        online=True,
        healthy=True,
        cpu_cores=cpu,
        memory_mb=memory,
        disk_mb=disk_mb,
        source="local_host_measurement",
        observed=True,
        capabilities=("python.test", "code.build", "device.status", "device.info"),
        metadata={"hostname": socket.gethostname()},
    )


def _android_nodes(device_bridge: Any) -> list[CloudNode]:
    nodes: list[CloudNode] = []
    for item in device_bridge.executor_capacities():
        nodes.append(
            CloudNode(
                node_id=str(item["executor_id"]),
                role="android_agent",
                platform=str(item.get("metadata", {}).get("platform", "android")),
                online=bool(item.get("online")),
                healthy=bool(item.get("healthy")),
                cpu_cores=float(item.get("cpu_cores", 0)),
                memory_mb=int(item.get("memory_mb", 0)),
                disk_mb=int(item.get("disk_mb", 0)),
                source="android_heartbeat",
                observed=True,
                capabilities=tuple(item.get("capabilities", ())),
                metadata=dict(item.get("metadata", {})),
            )
        )
    return nodes


class DeviceCloudPool:
    """One logical cloud resource pool backed by the Brain host and enrolled devices."""

    def __init__(self, device_bridge: Any):
        self.device_bridge = device_bridge

    def nodes(self) -> list[CloudNode]:
        return [local_host_node(), *_android_nodes(self.device_bridge)]

    def capacities(self) -> list[ExecutorCapacity]:
        capacities: list[ExecutorCapacity] = []
        for node in self.nodes():
            if not node.online or not node.healthy:
                continue
            capacities.append(
                ExecutorCapacity(
                    executor_id=node.node_id,
                    capabilities=frozenset(node.capabilities),
                    cpu_cores=node.cpu_cores,
                    memory_mb=node.memory_mb,
                    disk_mb=node.disk_mb,
                    tier="USER_DEVICE",
                    estimated_cost=0.0,
                    online=True,
                    healthy=True,
                    is_local=node.role == "compute_host",
                    host_id=node.node_id,
                    permissions=frozenset(node.capabilities),
                    metadata=node.metadata or {},
                )
            )
        return capacities

    def status(self) -> dict[str, Any]:
        nodes = self.nodes()
        android_seen = any(n.role == "android_agent" for n in nodes)
        return {
            "ok": True,
            "pool_id": "brain-device-cloud",
            "status": (
                "TWO_NODE_OBSERVED"
                if android_seen
                else "HOST_ONLY_ANDROID_NOT_OBSERVED"
            ),
            "nodes": [n.public() for n in nodes],
            "capacity_nodes": len(self.capacities()),
            "external_cloud_resources_created": False,
            "external_cloud_required": False,
            "execution_mode": "DEVICE_BACKED_SOFTWARE_CLOUD",
            "note": (
                "CPU/RAM/storage remain physical device resources; Brain exposes "
                "them as a managed software resource pool."
            ),
        }

    def plan(
        self,
        *,
        task_id: str,
        capability: str,
        demand: ResourceDemand | None = None,
        required_permissions: frozenset[str] = frozenset(),
        local_budget: LocalResourceBudget | None = None,
    ) -> ScheduleDecision:
        orchestrator = PortableResourceOrchestrator(
            local_budget=local_budget
            or LocalResourceBudget(
                max_cpu_cores_per_task=float(os.getenv("BRAIN_CLOUD_LOCAL_MAX_CPU", "1.0")),
                max_memory_mb_per_task=int(os.getenv("BRAIN_CLOUD_LOCAL_MAX_MEMORY_MB", "1024")),
                max_disk_mb_per_task=int(os.getenv("BRAIN_CLOUD_LOCAL_MAX_DISK_MB", "2048")),
                max_concurrent_tasks=int(os.getenv("BRAIN_CLOUD_LOCAL_MAX_CONCURRENCY", "1")),
            )
        )
        request = ScheduleRequest(
            task_id=task_id,
            capability=capability,
            demand=demand or ResourceDemand(),
            required_permissions=required_permissions,
            max_cost_usd=0.0,
            allow_paid=False,
        )
        return orchestrator.plan(request, self.capacities())
