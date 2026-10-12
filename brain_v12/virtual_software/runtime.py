"""Deterministic, declarative simulation of common software application classes.

This runtime models application lifecycle and resource requirements. It does not
execute arbitrary host binaries, access the host OS, or claim compatibility with
commercial applications unless an explicit native adapter is implemented.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
from threading import RLock
from typing import Any


@dataclass(frozen=True)
class ApplicationProfile:
    profile_id: str
    category: str
    display_name: str
    simulated_behaviors: tuple[str, ...]
    required_capabilities: tuple[str, ...] = ()
    min_memory_mib: int = 16
    min_storage_mib: int = 1
    network_required: bool = False
    fidelity: str = "WORKFLOW_SIMULATION"
    unsupported_behaviors: tuple[str, ...] = (
        "native binary execution", "unmodeled operating-system APIs",
        "real external side effects",
    )

    def describe(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id, "category": self.category,
            "display_name": self.display_name,
            "simulated_behaviors": list(self.simulated_behaviors),
            "required_capabilities": list(self.required_capabilities),
            "min_memory_mib": self.min_memory_mib,
            "min_storage_mib": self.min_storage_mib,
            "network_required": self.network_required, "fidelity": self.fidelity,
            "unsupported_behaviors": list(self.unsupported_behaviors),
        }


# These are behavior profiles for familiar application classes, not vendor
# implementations or claims that their proprietary binaries can run here.
_PROFILES = (
    ApplicationProfile("browser-workflow-v1", "browser", "Web Browser Workflow",
        ("tab lifecycle", "URL/navigation state", "cookie/storage model",
         "request/response fixtures", "basic page workflow"), ("filesystem",), 64, 8, True),
    ApplicationProfile("office-workflow-v1", "office", "Office Productivity Workflow",
        ("document create/edit/save", "spreadsheet cells/formulas subset",
         "presentation slide inventory", "import/export fixture validation"),
        ("filesystem",), 64, 32),
    ApplicationProfile("database-workflow-v1", "database", "Database Service Workflow",
        ("schema metadata", "parameterized query fixtures", "transaction commit/rollback",
         "connection-pool accounting"), ("filesystem",), 64, 32),
    ApplicationProfile("media-workflow-v1", "media", "Media Editor Workflow",
        ("timeline and track model", "asset inventory", "render-job queue",
         "export manifest and validation"), ("filesystem", "compute"), 128, 128),
    ApplicationProfile("developer-tool-workflow-v1", "developer-tools", "Developer Tool Workflow",
        ("project file inventory", "build-stage DAG", "test result fixtures",
         "artifact hashes", "dependency manifest validation"),
        ("filesystem", "compute"), 64, 64),
    ApplicationProfile("network-service-workflow-v1", "network-service", "Network Service Workflow",
        ("virtual endpoint registry", "request routing fixtures", "latency/loss simulation",
         "health and retry state"), ("network",), 32, 4, True),
)
PROFILE_CATALOG = {profile.profile_id: profile for profile in _PROFILES}


@dataclass
class VirtualApplication:
    app_id: str
    profile: ApplicationProfile
    config: dict[str, Any] = field(default_factory=dict)
    state: str = "CREATED"
    events: list[dict[str, Any]] = field(default_factory=list)
    _lock: RLock = field(default_factory=RLock, repr=False)

    def _event(self, event: str, **details: Any) -> dict[str, Any]:
        record = {"sequence": len(self.events) + 1, "event": event, **details}
        self.events.append(record)
        return record

    def start(self, machine_status: dict[str, Any] | None = None) -> dict[str, Any]:
        with self._lock:
            if self.state == "RUNNING":
                return {"ok": True, "status": self.state, "idempotent": True}
            machine_status = machine_status or {}
            if machine_status.get("powered") is False:
                return {"ok": False, "status": "BLOCKED", "reason": "VIRTUAL_MACHINE_POWERED_OFF"}
            capabilities = set(machine_status.get("capabilities", ()))
            missing = sorted(set(self.profile.required_capabilities) - capabilities)
            if missing:
                return {"ok": False, "status": "BLOCKED",
                        "reason": "APPLICATION_CAPABILITIES_MISSING", "missing_capabilities": missing}
            self.state = "RUNNING"
            self._event("STARTED", profile_id=self.profile.profile_id)
            return {"ok": True, "status": self.state, "app_id": self.app_id,
                    "fidelity": self.profile.fidelity, "native_execution": False}

    def perform(self, action: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Record a bounded declarative action; never evaluates supplied code."""
        with self._lock:
            if self.state != "RUNNING":
                return {"ok": False, "status": "REJECTED", "reason": "APPLICATION_NOT_RUNNING"}
            allowed = set(self.profile.simulated_behaviors)
            if action not in allowed:
                self._event("ACTION_REJECTED", action=action, reason="UNSUPPORTED_ACTION")
                return {"ok": False, "status": "REJECTED", "reason": "UNSUPPORTED_ACTION",
                        "allowed_actions": sorted(allowed)}
            safe_payload = payload or {}
            try:
                encoded = json.dumps(safe_payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
            except (TypeError, ValueError) as exc:
                return {"ok": False, "status": "REJECTED", "reason": "PAYLOAD_NOT_JSON_SAFE",
                        "detail": type(exc).__name__}
            digest = sha256(encoded.encode("utf-8")).hexdigest()
            event = self._event("ACTION_SIMULATED", action=action, payload_sha256=digest)
            return {"ok": True, "status": "SIMULATED", "event": event,
                    "payload_sha256": digest, "external_side_effects": False}

    def stop(self) -> dict[str, Any]:
        with self._lock:
            if self.state != "STOPPED":
                self.state = "STOPPED"
                self._event("STOPPED")
            return {"ok": True, "status": self.state, "app_id": self.app_id}

    def status(self) -> dict[str, Any]:
        return {"app_id": self.app_id, "profile": self.profile.describe(),
                "state": self.state, "event_count": len(self.events),
                "event_chain": list(self.events), "native_execution": False}


class VirtualSoftwareRuntime:
    """In-memory registry for deterministic application workflow simulations."""
    def __init__(self) -> None:
        self._apps: dict[str, VirtualApplication] = {}
        self._lock = RLock()

    @staticmethod
    def profiles() -> list[dict[str, Any]]:
        return [PROFILE_CATALOG[key].describe() for key in sorted(PROFILE_CATALOG)]

    def create(self, app_id: str, profile_id: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
        if not isinstance(app_id, str) or not app_id.strip():
            raise ValueError("APPLICATION_ID_REQUIRED")
        profile = PROFILE_CATALOG.get(profile_id)
        if profile is None:
            raise ValueError("UNKNOWN_APPLICATION_PROFILE")
        with self._lock:
            if app_id in self._apps:
                raise ValueError("VIRTUAL_APPLICATION_ALREADY_EXISTS")
            app = VirtualApplication(app_id=app_id, profile=profile, config=dict(config or {}))
            self._apps[app_id] = app
            return {"ok": True, "app_id": app_id, "profile": profile.describe(),
                    "status": app.status(), "registry_durability": "process-local"}

    def get(self, app_id: str) -> VirtualApplication:
        with self._lock:
            try:
                return self._apps[app_id]
            except KeyError as exc:
                raise KeyError("VIRTUAL_APPLICATION_NOT_FOUND") from exc

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            return [self._apps[key].status() for key in sorted(self._apps)]
