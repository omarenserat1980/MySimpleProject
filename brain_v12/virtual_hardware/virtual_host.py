"""Integrated simulation-only host combining BrainVM tasks and virtual services.

This is a deterministic software model. It does not bind network ports, launch
host processes, reserve physical resources, or verify a guest operating system.
"""
from __future__ import annotations

from .task_runner import BrainVMTaskRunner
from .virtual_server_runtime import BrainVirtualServerRuntime


class BrainVirtualHost:
    """Compose a task scheduler and service runtime behind one lifecycle API."""

    def __init__(self, host_id: str = "brain-virtual-host-v1",
                 ram_cells_per_task: int = 65536, clock_width_bits: int = 32):
        if not isinstance(host_id, str) or not host_id.strip():
            raise ValueError("VIRTUAL_HOST_ID_REQUIRED")
        self.host_id = host_id.strip()
        self.tasks = BrainVMTaskRunner(
            ram_cells=ram_cells_per_task, clock_width_bits=clock_width_bits
        )
        self.server = BrainVirtualServerRuntime(server_id=self.host_id)
        self.events: list[dict] = []

    def register_service(self, name: str, kind: str = "api") -> dict:
        result = self.server.register_service(name, kind)
        self._event("SERVICE_REGISTERED", name=name)
        return result

    def start_service(self, name: str) -> dict:
        result = self.server.start_service(name)
        self._event("SERVICE_STARTED", name=name)
        return result

    def create_task(self, name: str, program) -> str:
        pid = self.tasks.create_task(name, program)
        self._event("TASK_CREATED", name=name, pid=pid)
        return pid

    def run_tasks(self, max_ticks: int = 10000) -> dict:
        result = self.tasks.run(max_ticks=max_ticks)
        self._event("TASKS_SCHEDULED", ticks=result["ticks_this_run"],
                    completed=result["completed"])
        return result

    def request(self, service_name: str, operation: str = "health") -> dict:
        result = self.server.request(service_name, operation)
        self._event("SERVICE_REQUEST", name=service_name, ok=result["ok"])
        return result

    def health(self) -> dict:
        server_health = self.server.health()
        task_status = self.tasks.status()
        active = [
            task for task in self.tasks._tasks.values()
            if task["process"].state != "TERMINATED" and not task["board"].cpu.halted
        ]
        return {
            "ok": server_health["ok"],
            "mode": "SIMULATED_BRAIN_VIRTUAL_HOST",
            "host_id": self.host_id,
            "status": "DEGRADED" if not server_health["ok"] else (
                "READY" if server_health["running_services"] or task_status["task_count"] else "IDLE"
            ),
            "server": server_health,
            "scheduler": task_status,
            "active_task_count": len(active),
            "event_count": len(self.events),
            "network_listener_enabled": False,
            "guest_os_boot_verified": False,
            "physical_hardware": False,
        }

    def checkpoint(self) -> dict:
        """Capture service and complete task-runner state for simulation recovery."""
        return {
            "schema": "brain-virtual-host-checkpoint-v2",
            "mode": "SIMULATED_BRAIN_VIRTUAL_HOST",
            "host_id": self.host_id,
            "server": self.server.checkpoint(),
            "task_runner": self.tasks.checkpoint(),
            "events": [dict(event) for event in self.events],
            "task_programs_included": True,
            "network_listener_enabled": False,
            "physical_hardware": False,
            "guest_os_boot_verified": False,
        }

    def restore_checkpoint(self, checkpoint: dict) -> dict:
        """Restore both services and runnable tasks only after validating candidates."""
        if not isinstance(checkpoint, dict) or checkpoint.get("schema") != "brain-virtual-host-checkpoint-v2":
            raise ValueError("VIRTUAL_HOST_CHECKPOINT_SCHEMA_UNSUPPORTED")
        if checkpoint.get("mode") != "SIMULATED_BRAIN_VIRTUAL_HOST":
            raise ValueError("VIRTUAL_HOST_CHECKPOINT_MODE_INVALID")
        host_id = checkpoint.get("host_id")
        events = checkpoint.get("events")
        if not isinstance(host_id, str) or not host_id.strip():
            raise ValueError("VIRTUAL_HOST_CHECKPOINT_ID_INVALID")
        if not isinstance(events, list):
            raise ValueError("VIRTUAL_HOST_CHECKPOINT_EVENTS_INVALID")
        candidate_events = []
        for event in events:
            if not isinstance(event, dict) or not isinstance(event.get("type"), str):
                raise ValueError("VIRTUAL_HOST_CHECKPOINT_EVENT_INVALID")
            candidate_events.append(dict(event))

        # Construct candidates first; a failure must not mutate the live host.
        server_candidate = BrainVirtualServerRuntime()
        server_candidate.restore_checkpoint(checkpoint.get("server"))
        if server_candidate.server_id != host_id.strip():
            raise ValueError("VIRTUAL_HOST_CHECKPOINT_SERVER_ID_MISMATCH")
        task_candidate = BrainVMTaskRunner(
            ram_cells=self.tasks.ram_cells,
            clock_width_bits=self.tasks.clock_width_bits,
        )
        task_candidate.restore_checkpoint(checkpoint.get("task_runner"))
        if checkpoint.get("task_programs_included") is not True:
            raise ValueError("VIRTUAL_HOST_CHECKPOINT_PROGRAMS_MISSING")

        self.host_id = host_id.strip()
        self.server = server_candidate
        self.tasks = task_candidate
        self.events = candidate_events
        return {
            **self.health(),
            "restored_task_count": len(self.tasks._tasks),
            "tasks_resumed": True,
            "reason": "SIMULATED_TASK_PROGRAMS_AND_STATE_RESTORED",
        }

    def _event(self, event_type: str, **details) -> None:
        self.events.append({"type": event_type, **details})
