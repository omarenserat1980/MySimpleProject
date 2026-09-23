"""Continuous workforce evolution for the Electronic Brain.

The engine dynamically evaluates employees, creates capacity when needed,
promotes proven performers, reassigns weak fits, and retires persistently
underperforming specialists. It is intentionally bounded: creation and
resource usage have per-cycle limits, and external side effects remain
permission-gated.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .employee_hierarchy import Employee, EmployeeHierarchy
from .notifications import NotificationCenter


class WorkforceEvolutionEngine:
    def __init__(
        self,
        organization: EmployeeHierarchy,
        notifications: NotificationCenter,
        *,
        max_active_workers: int = 1000,
        max_new_per_cycle: int = 5,
    ) -> None:
        self.organization = organization
        self.notifications = notifications
        self.max_active_workers = max_active_workers
        self.max_new_per_cycle = max_new_per_cycle

    @staticmethod
    def performance_score(employee: Employee) -> float:
        total = employee.completed_tasks + employee.failed_tasks
        if total == 0:
            return 0.5
        success = employee.completed_tasks / total
        experience = min(employee.completed_tasks / 20.0, 1.0)
        return round((success * 0.75) + (experience * 0.25), 4)

    def _active_workers(self) -> int:
        return sum(e.status != "RETIRED" for e in self.organization.employees.values())

    def _available_workers(self) -> int:
        return sum(e.status == "AVAILABLE" for e in self.organization.employees.values())

    def _retire_weak(self) -> list[str]:
        retired: list[str] = []
        for employee in self.organization.employees.values():
            total = employee.completed_tasks + employee.failed_tasks
            if employee.status == "RETIRED" or total < 8:
                continue
            score = self.performance_score(employee)
            if score < 0.35 and employee.status != "BUSY":
                employee.status = "RETIRED"
                employee.current_task_id = None
                retired.append(employee.employee_id)
                self.notifications.emit(
                    "EMPLOYEE_RETIRED",
                    sender_id="BRAIN-001",
                    recipient_id=employee.manager_id,
                    message=f"{employee.employee_id} retired after sustained underperformance",
                    priority="NORMAL",
                    data={"performance_score": score},
                )
        return retired

    def _promote_proven(self) -> list[str]:
        promoted: list[str] = []
        for employee in self.organization.employees.values():
            if employee.status == "RETIRED":
                continue
            total = employee.completed_tasks + employee.failed_tasks
            score = self.performance_score(employee)
            if total >= 5 and score >= 0.90 and employee.title not in {
                "Senior Specialist", "Team Supervisor", "Department Manager"
            }:
                employee.title = f"Senior {employee.title}"
                promoted.append(employee.employee_id)
                self.notifications.emit(
                    "EMPLOYEE_PROMOTED",
                    sender_id="BRAIN-001",
                    recipient_id=employee.manager_id,
                    message=f"{employee.employee_id} promoted after sustained strong performance",
                    priority="NORMAL",
                    data={"performance_score": score, "completed_tasks": employee.completed_tasks},
                )
        return promoted

    def _replace_retired(self, retired_ids: list[str]) -> list[Employee]:
        """Maintain workforce continuity by replacing retired workers."""
        created: list[Employee] = []
        for retired_id in retired_ids[: self.max_new_per_cycle]:
            retired = self.organization.employees.get(retired_id)
            if retired is None:
                continue
            replacement = self.organization.add_employees(
                1,
                department_id=retired.department_id,
                title=f"Replacement {retired.title}",
                skills=tuple(retired.skills) or ("general",),
            )
            created.extend(replacement)
            for employee in replacement:
                self.notifications.emit(
                    "EMPLOYEE_REPLACED",
                    sender_id="BRAIN-001",
                    recipient_id=employee.manager_id,
                    message=f"Created {employee.employee_id} to replace retired {retired_id}",
                    priority="HIGH",
                    data={"retired_employee": retired_id, "skills": list(employee.skills)},
                )
        return created

    def _create_capacity(self, objective: str) -> list[Employee]:
        if self._active_workers() >= self.max_active_workers:
            return []

        pressure = max(0, self._available_workers() == 0)
        # A short list of objective signals gives new workers a useful initial skill profile.
        lowered = objective.lower()
        if any(k in lowered for k in ("فيديو", "video", "cinematic", "سينمائي")):
            title, skills, department = (
                "Dynamic Media Specialist",
                ("media", "video", "cinematic", "quality"),
                "DEPT-005",
            )
        elif any(k in lowered for k in ("كود", "برمج", "software", "code", "api")):
            title, skills, department = (
                "Dynamic Engineering Specialist",
                ("software", "automation", "testing"),
                "DEPT-004",
            )
        elif any(k in lowered for k in ("بحث", "research", "market", "فرصة")):
            title, skills, department = (
                "Dynamic Research Specialist",
                ("research", "verification", "opportunity_discovery"),
                "DEPT-002",
            )
        else:
            title, skills, department = (
                "Dynamic Operations Specialist",
                ("general", "planning", "execution"),
                "DEPT-007",
            )

        # Create only when capacity pressure or a capability-specific objective exists.
        if not pressure and self._active_workers() >= max(10, self._available_workers() + 2):
            return []
        created = self.organization.add_employees(
            min(self.max_new_per_cycle, 1),
            department_id=department,
            title=title,
            skills=skills,
        )
        for employee in created:
            self.notifications.emit(
                "EMPLOYEE_CREATED",
                sender_id="BRAIN-001",
                recipient_id=employee.manager_id,
                message=f"Created {employee.employee_id} for dynamic capacity",
                priority="NORMAL",
                data={"objective": objective, "skills": list(employee.skills)},
            )
        return created

    def evolve(self, objective: str) -> dict[str, Any]:
        retired = self._retire_weak()
        promoted = self._promote_proven()
        replacements = self._replace_retired(retired)
        created = list(replacements)
        if not replacements:
            created.extend(self._create_capacity(objective))
        return {
            "created": [asdict(e) for e in created],
            "replacement_count": len(replacements),
            "promoted": promoted,
            "retired": retired,
            "active_workers": self._active_workers(),
            "available_workers": self._available_workers(),
            "max_active_workers": self.max_active_workers,
            "max_new_per_cycle": self.max_new_per_cycle,
            "continuous_evolution": True,
        }
