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
        """Capture a recoverable manifest; task program state is intentionally excluded."""
        return {
            "schema": "brain-virtual-host-checkpoint-v1",
            "mode": "SIMULATED_BRAIN_VIRTUAL_HOST",
            "host_id": self.host_id,
            "server": self.server.checkpoint(),
            "events": [dict(event) for event in self.events],
            "task_manifest": [
                {
                    "pid": pid,
                    "name": task["process"].name,
                    "state": task["process"].state,
                    "instructions_executed": task["steps"],
                    "board_checkpoint": task["board"].checkpoint(),
                }
                for pid, task in self.tasks._tasks.items()
            ],
            "task_programs_included": False,
            "network_listener_enabled": False,
            "physical_hardware": False,
        }

    def restore_checkpoint(self, checkpoint: dict) -> dict:
        """Restore service state and validate the host manifest without claiming task resume."""
        if not isinstance(checkpoint, dict) or checkpoint.get("schema") != "brain-virtual-host-checkpoint-v1":
            raise ValueError("VIRTUAL_HOST_CHECKPOINT_SCHEMA_UNSUPPORTED")
        if checkpoint.get("mode") != "SIMULATED_BRAIN_VIRTUAL_HOST":
            raise ValueError("VIRTUAL_HOST_CHECKPOINT_MODE_INVALID")
        host_id = checkpoint.get("host_id")
        events = checkpoint.get("events")
        task_manifest = checkpoint.get("task_manifest")
        if not isinstance(host_id, str) or not host_id.strip():
            raise ValueError("VIRTUAL_HOST_CHECKPOINT_ID_INVALID")
        if not isinstance(events, list) or not isinstance(task_manifest, list):
            raise ValueError("VIRTUAL_HOST_CHECKPOINT_COLLECTIONS_INVALID")
        candidate_events = []
        for event in events:
            if not isinstance(event, dict) or not isinstance(event.get("type"), str):
                raise ValueError("VIRTUAL_HOST_CHECKPOINT_EVENT_INVALID")
            candidate_events.append(dict(event))
        # Task programs are not serialized; refuse to imply they can resume autonomously.
        for item in task_manifest:
            if not isinstance(item, dict) or not isinstance(item.get("board_checkpoint"), dict):
                raise ValueError("VIRTUAL_HOST_CHECKPOINT_TASK_INVALID")
            if not isinstance(item.get("name"), str) or not isinstance(item.get("pid"), str):
                raise ValueError("VIRTUAL_HOST_CHECKPOINT_TASK_INVALID")
            if item.get("state") not in {"READY", "RUNNING", "TERMINATED"}:
                raise ValueError("VIRTUAL_HOST_CHECKPOINT_TASK_STATE_INVALID")
        server_candidate = BrainVirtualServerRuntime()
        server_candidate.restore_checkpoint(checkpoint.get("server"))
        # Validate all board snapshots against a fresh board before changing live state.
        from .execution_board import BrainVMExecutionBoard
        for item in task_manifest:
            board_candidate = BrainVMExecutionBoard(
                ram_cells=self.tasks.ram_cells,
                clock_width_bits=self.tasks.clock_width_bits,
            )
            board_candidate.restore_checkpoint(item["board_checkpoint"])
            if item.get("instructions_executed") != board_candidate.instructions_executed:
                raise ValueError("VIRTUAL_HOST_CHECKPOINT_TASK_COUNTER_MISMATCH")
        self.host_id = host_id.strip()
        self.server = server_candidate
        self.events = candidate_events
        # Scheduler tasks are not resumed because their program bodies are not included.
        self.tasks = BrainVMTaskRunner(
            ram_cells=self.tasks.ram_cells, clock_width_bits=self.tasks.clock_width_bits
        )
        return {
            **self.health(),
            "restored_task_snapshots": len(task_manifest),
            "tasks_resumed": False,
            "reason": "PROGRAMS_NOT_INCLUDED_IN_HOST_CHECKPOINT",
        }

    def _event(self, event_type: str, **details) -> None:
        self.events.append({"type": event_type, **details})
