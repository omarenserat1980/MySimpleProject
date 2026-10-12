"""Portable, policy-first resource scheduling for Electronic Brain.

This module is deliberately side-effect free: it plans execution only. It does not
provision cloud resources, start workers, change host settings, or execute tasks.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
from typing import Any, Iterable


@dataclass(frozen=True)
class ResourceDemand:
    cpu_cores: float = 1.0
    memory_mb: int = 512
    disk_mb: int = 256
    gpu_count: int = 0
    timeout_seconds: int = 300

    def __post_init__(self) -> None:
        if self.cpu_cores < 0 or self.memory_mb < 0 or self.disk_mb < 0:
            raise ValueError("resource demand cannot be negative")
        if self.gpu_count < 0 or self.timeout_seconds <= 0:
            raise ValueError("gpu_count must be non-negative and timeout_seconds positive")


@dataclass(frozen=True)
class ExecutorCapacity:
    executor_id: str
    capabilities: frozenset[str]
    cpu_cores: float
    memory_mb: int
    disk_mb: int
    gpu_count: int = 0
    tier: str = "BRAIN_OWNED"
    estimated_cost: float = 0.0
    currency: str = "USD"
    online: bool = True
    healthy: bool = True
    is_local: bool = False
    host_id: str | None = None
    permissions: frozenset[str] = frozenset()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.executor_id:
            raise ValueError("executor_id is required")
        if min(self.cpu_cores, self.memory_mb, self.disk_mb, self.gpu_count, self.estimated_cost) < 0:
            raise ValueError("executor capacity and cost cannot be negative")
        if self.currency != "USD":
            raise ValueError("cost estimates must be normalized to USD before scheduling")


@dataclass(frozen=True)
class LocalResourceBudget:
    """Hard ceiling for work delegated to the selected local host."""
    max_cpu_cores_per_task: float = 0.25
    max_memory_mb_per_task: int = 256
    max_disk_mb_per_task: int = 512
    max_concurrent_tasks: int = 1


@dataclass(frozen=True)
class ScheduleRequest:
    task_id: str
    capability: str
    demand: ResourceDemand = field(default_factory=ResourceDemand)
    required_permissions: frozenset[str] = frozenset()
    max_cost_usd: float = 0.0
    allow_paid: bool = False
    preferred_host_id: str | None = None
    intent: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.task_id or not self.capability:
            raise ValueError("task_id and capability are required")
        if self.max_cost_usd < 0:
            raise ValueError("max_cost_usd cannot be negative")
        if not self.allow_paid and self.max_cost_usd != 0:
            raise ValueError("nonzero max_cost_usd requires allow_paid=True")


@dataclass(frozen=True)
class ScheduleDecision:
    status: str
    task_id: str
    executor_id: str | None
    reason: str
    estimated_cost_usd: float = 0.0
    rejected: tuple[dict[str, str], ...] = ()
    intent_hash: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def intent_digest(request: ScheduleRequest) -> str:
    """Stable digest for the task intent; never includes secrets."""
    payload = {
        "task_id": request.task_id,
        "capability": request.capability,
        "demand": asdict(request.demand),
        "required_permissions": sorted(request.required_permissions),
        "intent": request.intent,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256(encoded.encode("utf-8")).hexdigest()


def _fits(demand: ResourceDemand, executor: ExecutorCapacity) -> bool:
    return (
        demand.cpu_cores <= executor.cpu_cores
        and demand.memory_mb <= executor.memory_mb
        and demand.disk_mb <= executor.disk_mb
        and demand.gpu_count <= executor.gpu_count
    )


def _tier_rank(executor: ExecutorCapacity) -> int:
    # Remote free/Brain-owned capacity is preferred over consuming local host
    # resources. Paid capacity is only considered after explicit opt-in.
    if executor.tier in {"BRAIN_OWNED", "FREE_CI", "FREE_CLOUD", "FREE_DIVERSE"}:
        return 0 if not executor.is_local else 2
    if executor.tier in {"USER_DEVICE", "LOCAL"}:
        return 3
    if executor.tier in {"PAID_EXTERNAL", "PAID_CLOUD"}:
        return 4
    return 5


class PortableResourceOrchestrator:
    """Deterministic, fail-closed scheduler; planning only, with no side effects."""

    def __init__(
        self,
        *,
        local_budget: LocalResourceBudget | None = None,
        local_concurrent_tasks: int = 0,
        default_allow_paid: bool = False,
    ) -> None:
        self.local_budget = local_budget or LocalResourceBudget()
        self.local_concurrent_tasks = max(0, int(local_concurrent_tasks))
        self.default_allow_paid = bool(default_allow_paid)

    def plan(
        self,
        request: ScheduleRequest,
        executors: Iterable[ExecutorCapacity],
    ) -> ScheduleDecision:
        rejected: list[dict[str, str]] = []
        candidates: list[ExecutorCapacity] = []
        allow_paid = request.allow_paid and self.default_allow_paid

        for executor in executors:
            reason = None
            if not executor.online:
                reason = "OFFLINE"
            elif not executor.healthy:
                reason = "UNHEALTHY"
            elif request.capability not in executor.capabilities:
                reason = "CAPABILITY_MISSING"
            elif not request.required_permissions.issubset(executor.permissions):
                reason = "PERMISSION_MISSING"
            elif not _fits(request.demand, executor):
                reason = "INSUFFICIENT_CAPACITY"
            elif executor.estimated_cost > 0 and not allow_paid:
                reason = "PAID_DISABLED"
            elif executor.estimated_cost > request.max_cost_usd:
                reason = "COST_LIMIT_EXCEEDED"
            elif executor.estimated_cost > 0 and executor.tier not in {"PAID_EXTERNAL", "PAID_CLOUD"}:
                reason = "UNKNOWN_COST_TIER"
            elif executor.is_local and (
                request.demand.cpu_cores > self.local_budget.max_cpu_cores_per_task
                or request.demand.memory_mb > self.local_budget.max_memory_mb_per_task
                or request.demand.disk_mb > self.local_budget.max_disk_mb_per_task
                or self.local_concurrent_tasks >= self.local_budget.max_concurrent_tasks
            ):
                reason = "LOCAL_RESOURCE_BUDGET_EXCEEDED"

            if reason:
                rejected.append({"executor_id": executor.executor_id, "reason": reason})
            else:
                candidates.append(executor)

        if not candidates:
            return ScheduleDecision(
                status="BLOCKED_NO_EXECUTOR",
                task_id=request.task_id,
                executor_id=None,
                reason="No executor passed capability, health, permission, capacity, and cost gates.",
                rejected=tuple(rejected),
                intent_hash=intent_digest(request),
            )

        candidates.sort(key=lambda e: (
            _tier_rank(e),
            e.estimated_cost,
            -e.cpu_cores,
            -e.memory_mb,
            e.executor_id,
        ))
        chosen = candidates[0]
        return ScheduleDecision(
            status="PLANNED",
            task_id=request.task_id,
            executor_id=chosen.executor_id,
            reason="Selected by deterministic policy; execution has not started.",
            estimated_cost_usd=chosen.estimated_cost,
            rejected=tuple(rejected),
            intent_hash=intent_digest(request),
        )
