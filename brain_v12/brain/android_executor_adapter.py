"""Discover explicitly enrolled Android executors for portable scheduling.

Device heartbeat alone is not proof of capability or permission. A device becomes
schedulable only when its heartbeat metadata explicitly marks it enrolled and
advertises bounded resource capacities and capabilities.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping
import time

from .portable_resource_orchestrator import ExecutorCapacity

ANDROID_PREFIX = "android-executor-"
ALLOWED_CAPABILITIES = frozenset({
    "python.test", "code.build", "device.status", "device.info",
    "media.image", "media.render",
})


def android_executor_capacities(
    agents: Iterable[Mapping[str, Any]],
    *,
    now: float | None = None,
    heartbeat_ttl_seconds: float = 30.0,
) -> list[ExecutorCapacity]:
    """Convert live heartbeat records to scheduler candidates; fail closed by default.

    Expected record shape: agent_id, last_seen, metadata. Metadata must include
    enrolled=true, capabilities, and non-negative cpu_cores/memory_mb/disk_mb.
    Capabilities are intersected with a strict allowlist; the adapter never
    grants permissions and never advertises arbitrary shell execution.
    """
    current = time.time() if now is None else float(now)
    if heartbeat_ttl_seconds <= 0:
        raise ValueError("heartbeat_ttl_seconds must be positive")
    candidates: list[ExecutorCapacity] = []
    for agent in agents:
        agent_id = str(agent.get("agent_id", ""))
        if not agent_id.startswith(ANDROID_PREFIX):
            continue
        try:
            last_seen = float(agent.get("last_seen", 0))
        except (TypeError, ValueError):
            continue
        age = current - last_seen
        if age < 0 or age > heartbeat_ttl_seconds:
            continue
        metadata = agent.get("metadata")
        if not isinstance(metadata, Mapping) or metadata.get("enrolled") is not True:
            continue
        raw_capabilities = metadata.get("capabilities", ())
        if not isinstance(raw_capabilities, (list, tuple, set, frozenset)):
            continue
        capabilities = frozenset(str(item) for item in raw_capabilities) & ALLOWED_CAPABILITIES
        if not capabilities:
            continue
        try:
            cpu = float(metadata["cpu_cores"])
            memory = int(metadata["memory_mb"])
            disk = int(metadata["disk_mb"])
            gpu = int(metadata.get("gpu_count", 0))
        except (KeyError, TypeError, ValueError):
            continue
        if min(cpu, memory, disk, gpu) < 0 or cpu == 0 or memory == 0 or disk == 0:
            continue
        permissions_raw = metadata.get("permissions", ())
        if not isinstance(permissions_raw, (list, tuple, set, frozenset)):
            permissions_raw = ()
        permissions = frozenset(str(item) for item in permissions_raw if str(item) in {
            "device", "python.test", "code.build", "media.image", "media.render"
        })
        candidates.append(ExecutorCapacity(
            executor_id=agent_id,
            capabilities=capabilities,
            cpu_cores=cpu,
            memory_mb=memory,
            disk_mb=disk,
            gpu_count=gpu,
            tier="USER_DEVICE",
            estimated_cost=0.0,
            online=True,
            healthy=metadata.get("healthy") is True,
            is_local=False,
            host_id=str(metadata.get("host_id") or agent_id),
            permissions=permissions,
            metadata={
                "platform": "android",
                "model": str(metadata.get("model", "unknown")),
                "android_version": str(metadata.get("android_version", "unknown")),
                "heartbeat_age_seconds": round(age, 2),
                "enrollment_version": str(metadata.get("enrollment_version", "1")),
            },
        ))
    return sorted(candidates, key=lambda item: item.executor_id)
