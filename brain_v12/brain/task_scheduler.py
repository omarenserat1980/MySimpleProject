"""Initial policy-only scheduler skeleton for Electronic Brain.

This prototype only selects among explicitly supplied resource records. It does
not launch tasks, claim leases, provision cloud capacity, or contact devices.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from brain_v12.brain.resource_fabric import ResourceRecord, ResourceState


class ScheduleStatus(str, Enum):
    SELECTED = "SELECTED"
    DEFERRED = "DEFERRED"
    NO_RESOURCE = "NO_RESOURCE"


@dataclass(frozen=True)
class TaskRequest:
    task_id: str
    required_vcpu: int = 1
    required_memory_mb: int = 512
    required_storage_gb: int = 0

    def __post_init__(self) -> None:
        if not self.task_id.strip():
            raise ValueError("TASK_ID_REQUIRED")
        if self.required_vcpu < 1 or self.required_memory_mb < 1 or self.required_storage_gb < 0:
            raise ValueError("TASK_RESOURCE_REQUIREMENTS_INVALID")


@dataclass(frozen=True)
class ScheduleDecision:
    task_id: str
    status: ScheduleStatus
    resource_id: str | None
    reason: str


def _fits(task: TaskRequest, resource: ResourceRecord) -> bool:
    values = (resource.vcpu, resource.memory_mb, resource.storage_gb)
    if any(value is None for value in values):
        return False
    return (
        resource.vcpu >= task.required_vcpu
        and resource.memory_mb >= task.required_memory_mb
        and resource.storage_gb >= task.required_storage_gb
    )


def select_resource(task: TaskRequest, resources: Iterable[ResourceRecord]) -> ScheduleDecision:
    """Choose a fitting AVAILABLE resource deterministically; never execute."""
    candidates = sorted(
        (resource for resource in resources if resource.state == ResourceState.AVAILABLE and _fits(task, resource)),
        key=lambda resource: (resource.vcpu, resource.memory_mb, resource.storage_gb, resource.resource_id),
    )
    if candidates:
        return ScheduleDecision(task.task_id, ScheduleStatus.SELECTED, candidates[0].resource_id,
                                "POLICY_SELECTION_ONLY_NOT_EXECUTED")
    known_available = any(resource.state == ResourceState.AVAILABLE for resource in resources)
    if known_available:
        return ScheduleDecision(task.task_id, ScheduleStatus.DEFERRED, None,
                                "NO_AVAILABLE_RESOURCE_MEETS_REQUIREMENTS")
    return ScheduleDecision(task.task_id, ScheduleStatus.NO_RESOURCE, None,
                            "NO_CONFIRMED_AVAILABLE_RESOURCE")
