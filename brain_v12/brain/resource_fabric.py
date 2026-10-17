"""Initial skeleton for Brain's provider-neutral resource fabric.

This is a prototype contract only. It does not discover devices, contact providers,
schedule tasks, allocate capacity, or claim that a resource is online.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ResourceState(str, Enum):
    UNKNOWN = "UNKNOWN"
    AVAILABLE = "AVAILABLE"
    BUSY = "BUSY"
    OFFLINE = "OFFLINE"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class ResourceRecord:
    resource_id: str
    kind: str
    source: str
    state: ResourceState = ResourceState.UNKNOWN
    vcpu: int | None = None
    memory_mb: int | None = None
    storage_gb: int | None = None
    evidence_ref: str | None = None
    metadata: dict[str, Any] | None = None


class ResourceFabric:
    """Minimal in-memory registry for a future unified resource view."""

    def __init__(self) -> None:
        self._resources: dict[str, ResourceRecord] = {}

    def register(self, resource: ResourceRecord) -> None:
        """Register a resource record; duplicate IDs are rejected."""
        if not resource.resource_id.strip():
            raise ValueError("RESOURCE_ID_REQUIRED")
        if resource.resource_id in self._resources:
            raise ValueError("RESOURCE_ALREADY_REGISTERED")
        self._resources[resource.resource_id] = resource

    def get(self, resource_id: str) -> ResourceRecord | None:
        """Return one registered record, or None when it is unknown."""
        return self._resources.get(resource_id)

    def list_resources(self) -> tuple[ResourceRecord, ...]:
        """Return a stable snapshot of registered records."""
        return tuple(self._resources[key] for key in sorted(self._resources))
