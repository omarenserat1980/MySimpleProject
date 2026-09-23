"""Dedicated workforce for continuous improvement of the Brain coding tool.

The team creates an auditable improvement queue and uses CodeWorkspaceTool for
bounded source changes. It never stores credentials, transfers money, or
publishes externally.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from time import time
from typing import Any, Iterable

from .code_workspace_tool import CodeChange, CodeWorkspaceTool
from .employee_hierarchy import EmployeeHierarchy


@dataclass
class CodingImprovement:
    improvement_id: str
    objective: str
    priority: float = 0.5
    status: str = "QUEUED"
    created_at: float = field(default_factory=time)
    result: dict[str, Any] = field(default_factory=dict)


class CodeToolEngineeringTeam:
    """Permanent specialist team responsible only for the Brain coding tool."""

    TEAM_DEPARTMENT = "DEPT-CODE-TOOL"
    TEAM_TITLE = "BRAIN_CODE_TOOL_ONLY"

    def __init__(self, organization: EmployeeHierarchy, workspace: CodeWorkspaceTool) -> None:
        self.organization = organization
        self.workspace = workspace
        self.team = organization.ensure_specialized_team(department_id=self.TEAM_DEPARTMENT)
        self.queue: list[CodingImprovement] = []
        self.cycles = 0

    @property
    def employee_ids(self) -> tuple[str, ...]:
        return tuple(self.team["employee_ids"])

    def enqueue(self, objective: str, *, priority: float = 0.5) -> CodingImprovement:
        item = CodingImprovement(
            improvement_id=f"CODE-IMP-{len(self.queue)+1:06d}",
            objective=str(objective).strip(),
            priority=max(0.0, min(1.0, float(priority))),
        )
        self.queue.append(item)
        return item

    def plan_cycle(self) -> dict[str, Any]:
        """Create bounded work for the specialist team without inventing code changes."""
        self.cycles += 1
        if not self.queue:
            self.enqueue("inspect the coding tool for the highest-value safe improvement", priority=0.8)
            self.enqueue("add regression coverage for the coding tool", priority=0.75)
            self.enqueue("measure reliability, rollback, and validation paths", priority=0.7)
        pending = sorted(
            (x for x in self.queue if x.status == "QUEUED"),
            key=lambda x: x.priority,
            reverse=True,
        )
        assignments = []
        for index, item in enumerate(pending[: len(self.employee_ids)]):
            employee_id = self.employee_ids[index]
            assignments.append({
                "improvement_id": item.improvement_id,
                "employee_id": employee_id,
                "objective": item.objective,
                "priority": item.priority,
            })
        return {
            "cycle": self.cycles,
            "team_department": self.TEAM_DEPARTMENT,
            "specialization": self.TEAM_TITLE,
            "employee_count": len(self.employee_ids),
            "assignments": assignments,
        }

    def validate_change(self, changes: Iterable[CodeChange]) -> dict[str, Any]:
        """Dry-run a proposed change before any write occurs."""
        return self.workspace.dry_run(list(changes), validate_python=True)

    def apply_change(self, changes: Iterable[CodeChange], *, reason: str = "") -> dict[str, Any]:
        """Apply an already-proposed safe change atomically with rollback on validation failure."""
        changes = list(changes)
        checkpoint = self.workspace.checkpoint([c.path for c in changes])
        results = self.workspace.apply(changes, validate_python=True)
        return {
            "status": "APPLIED",
            "reason": reason,
            "checkpoint": checkpoint,
            "results": [asdict(x) for x in results],
        }

    def verify(self, paths: Iterable[str] = ()) -> dict[str, Any]:
        return self.workspace.verify(paths)

    def snapshot(self) -> dict[str, Any]:
        return {
            "specialization": self.TEAM_TITLE,
            "department_id": self.TEAM_DEPARTMENT,
            "manager_id": self.team["manager_id"],
            "employee_ids": list(self.employee_ids),
            "employee_count": len(self.employee_ids),
            "continuous_improvement": True,
            "cycles": self.cycles,
            "queue": [asdict(x) for x in self.queue[-50:]],
            "workspace": self.workspace.snapshot(),
            "external_side_effects": False,
            "credential_storage": False,
            "money_movement": False,
        }
