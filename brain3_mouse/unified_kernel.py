"""Shared in-process kernel foundation for Brain 3.

This module provides one memory store, one task queue, and one capability
registry for adapters from legacy Brain and Brain V12. It deliberately does
not import either runtime implicitly: integration must register real in-process
adapters and pass contract tests before the kernel reports them as available.
No network, Render, device, shell, or OS-boot actions are implemented here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
from typing import Any, Callable

ALLOWED_ACTIONS = frozenset({"inspect", "test", "plan"})
BLOCKED_ACTIONS = frozenset({"execute", "deploy", "render", "windows_boot", "device_setup", "publish"})


@dataclass
class ComponentAdapter:
    name: str
    capabilities: frozenset[str]
    handler: Callable[[str, dict[str, Any]], dict[str, Any]]
    verified: bool = False


@dataclass
class UnifiedBrainKernel:
    """A single shared coordination boundary; adapters do not own separate queues."""

    _lock: RLock = field(default_factory=RLock, init=False, repr=False)
    _memory: dict[str, Any] = field(default_factory=dict, init=False, repr=False)
    _tasks: list[dict[str, Any]] = field(default_factory=list, init=False, repr=False)
    _adapters: dict[str, ComponentAdapter] = field(default_factory=dict, init=False, repr=False)
    _next_id: int = field(default=1, init=False, repr=False)

    def register_adapter(self, adapter: ComponentAdapter) -> None:
        """Register a real in-process adapter after its caller verifies the contract."""
        if not adapter.name.strip() or not adapter.capabilities:
            raise ValueError("adapter name and at least one capability are required")
        if not adapter.capabilities <= ALLOWED_ACTIONS:
            raise ValueError("adapter requested a capability outside the safe allowlist")
        with self._lock:
            self._adapters[adapter.name] = adapter

    def adapter_status(self) -> dict[str, Any]:
        with self._lock:
            return {
                name: {"registered": True, "verified": item.verified,
                       "capabilities": sorted(item.capabilities)}
                for name, item in sorted(self._adapters.items())
            }

    def memory_get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._memory.get(key, default)

    def memory_set(self, key: str, value: Any) -> None:
        if not key or len(key) > 256:
            raise ValueError("memory key is required and must be <=256 characters")
        with self._lock:
            self._memory[key] = value

    def submit(self, action: str, description: str, requested_by: str = "brain3") -> dict[str, Any]:
        """Create work in the one shared queue; safe actions only, never auto-executed."""
        action = action.strip().lower()
        description = description.strip()
        if action in BLOCKED_ACTIONS:
            raise PermissionError(f"action blocked by Brain 3 policy: {action}")
        if action not in ALLOWED_ACTIONS:
            raise ValueError("action must be inspect, test, or plan")
        if not description or len(description) > 2000:
            raise ValueError("description is required and must be <=2000 characters")
        with self._lock:
            task = {
                "id": self._next_id,
                "action": action,
                "description": description,
                "requested_by": requested_by,
                "source": requested_by,
                "state": "QUEUED",
                "executed": False,
                "emulated": True,
                "remote_calls": False,
                "render": False,
                "physical_devices": False,
                "windows_boot_verified": False,
                "queue": "brain3_shared",
            }
            self._next_id += 1
            self._tasks.append(task)
            return dict(task)

    def tasks(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(task) for task in self._tasks]

    def dispatch(self, task_id: int, adapter_name: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Dispatch only to a verified in-process adapter; never performs OS/deploy work."""
        with self._lock:
            task = next((t for t in self._tasks if t["id"] == task_id), None)
            if task is None:
                raise KeyError("task not found")
            adapter = self._adapters.get(adapter_name)
            if adapter is None or not adapter.verified:
                raise PermissionError("adapter is not registered and verified")
            if task["action"] not in adapter.capabilities:
                raise PermissionError("adapter does not support this safe action")
            # Mark dispatch atomically to prevent duplicate execution races.
            if task["state"] != "QUEUED":
                raise ValueError("task is not queued")
            task["state"] = "RUNNING"
        try:
            result = adapter.handler(task["action"], dict(payload or {}))
            if not isinstance(result, dict):
                raise TypeError("adapter result must be a dictionary")
        except Exception as exc:
            with self._lock:
                task["state"] = "FAILED"
                task["error_type"] = type(exc).__name__
            raise
        with self._lock:
            task["state"] = "COMPLETED"
            task["executed"] = True
            task["adapter"] = adapter_name
            task["result"] = result
            return dict(task)

    def health(self) -> dict[str, Any]:
        with self._lock:
            return {
                "kernel": "Brain3UnifiedKernel",
                "shared_memory": True,
                "shared_task_queue": True,
                "registered_adapters": sorted(self._adapters),
                "legacy_brain_integrated": "legacy_brain" in self._adapters and self._adapters["legacy_brain"].verified,
                "brain_v12_integrated": "brain_v12" in self._adapters and self._adapters["brain_v12"].verified,
                "render": False,
                "external_network": False,
                "physical_devices": False,
                "windows_boot_verified": False,
                "production_ready": False,
            }


KERNEL = UnifiedBrainKernel()
