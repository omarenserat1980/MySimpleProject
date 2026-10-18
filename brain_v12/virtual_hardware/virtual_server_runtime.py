"""Simulation-first virtual server runtime with an explicit service registry.

This is an in-memory control-plane model, not a listening network server. It
never opens sockets, launches host processes, or claims guest OS boot evidence.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


_ALLOWED_KINDS = {"api", "web", "worker", "database", "monitoring"}
_ALLOWED_STATES = {"STOPPED", "RUNNING", "FAILED"}


@dataclass
class VirtualService:
    name: str
    kind: str
    state: str = "STOPPED"
    requests: int = 0
    failures: int = 0


class BrainVirtualServerRuntime:
    """Manage simulated services and deterministic request/health observations."""

    def __init__(self, server_id: str = "brain-server-small-v1"):
        if not isinstance(server_id, str) or not server_id.strip():
            raise ValueError("SERVER_ID_REQUIRED")
        self.server_id = server_id.strip()
        self.services: dict[str, VirtualService] = {}
        self.events: list[dict[str, Any]] = []
        self.tick = 0

    def register_service(self, name: str, kind: str = "api") -> dict:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("SERVICE_NAME_REQUIRED")
        name = name.strip()
        if kind not in _ALLOWED_KINDS:
            raise ValueError("UNSUPPORTED_SERVICE_KIND")
        if name in self.services:
            raise ValueError("SERVICE_ALREADY_REGISTERED")
        service = VirtualService(name=name, kind=kind)
        self.services[name] = service
        self._event("SERVICE_REGISTERED", name=name, kind=kind)
        return asdict(service)

    def start_service(self, name: str) -> dict:
        service = self._get_service(name)
        if service.state == "RUNNING":
            return {"ok": True, "status": "ALREADY_RUNNING", "service": asdict(service)}
        service.state = "RUNNING"
        self._event("SERVICE_STARTED", name=name)
        return {"ok": True, "status": "RUNNING", "service": asdict(service)}

    def stop_service(self, name: str) -> dict:
        service = self._get_service(name)
        service.state = "STOPPED"
        self._event("SERVICE_STOPPED", name=name)
        return {"ok": True, "status": "STOPPED", "service": asdict(service)}

    def fail_service(self, name: str, reason: str = "SIMULATED_FAILURE") -> dict:
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("FAILURE_REASON_REQUIRED")
        service = self._get_service(name)
        service.state = "FAILED"
        service.failures += 1
        self._event("SERVICE_FAILED", name=name, reason=reason.strip())
        return {"ok": True, "status": "FAILED", "service": asdict(service)}

    def request(self, service_name: str, operation: str = "health") -> dict:
        service = self._get_service(service_name)
        self.tick += 1
        if service.state != "RUNNING":
            self._event("REQUEST_REJECTED", name=service_name, reason="SERVICE_NOT_RUNNING")
            return {
                "ok": False,
                "status": "SERVICE_NOT_RUNNING",
                "service": service_name,
                "tick": self.tick,
                "network_socket_opened": False,
            }
        if not isinstance(operation, str) or not operation.strip():
            raise ValueError("REQUEST_OPERATION_REQUIRED")
        service.requests += 1
        self._event("REQUEST_HANDLED", name=service_name, operation=operation.strip())
        return {
            "ok": True,
            "status": "SIMULATED_RESPONSE",
            "server_id": self.server_id,
            "service": service_name,
            "kind": service.kind,
            "operation": operation.strip(),
            "request_number": service.requests,
            "tick": self.tick,
            "network_socket_opened": False,
            "physical_hardware": False,
        }

    def health(self) -> dict:
        services = [asdict(service) for service in self.services.values()]
        running = sum(service["state"] == "RUNNING" for service in services)
        failed = sum(service["state"] == "FAILED" for service in services)
        return {
            "ok": failed == 0,
            "mode": "SIMULATED_VIRTUAL_SERVER_RUNTIME",
            "server_id": self.server_id,
            "status": "DEGRADED" if failed else ("READY" if running else "IDLE"),
            "service_count": len(services),
            "running_services": running,
            "failed_services": failed,
            "services": services,
            "tick": self.tick,
            "network_listener_enabled": False,
            "guest_os_boot_verified": False,
            "physical_hardware": False,
        }

    def _get_service(self, name: str) -> VirtualService:
        service = self.services.get(name)
        if service is None:
            raise KeyError("SERVICE_NOT_FOUND")
        return service

    def _event(self, event_type: str, **details) -> None:
        self.events.append({"tick": self.tick, "type": event_type, **details})
