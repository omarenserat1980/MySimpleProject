"""Scalable employee/manager hierarchy for the Electronic Brain.

Creates logical AI employees under managers and departments. This layer is
organizational only: it routes tasks and escalation; it never grants money,
credential, legal, or external-publication permissions.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from time import time
from typing import Any


@dataclass
class Employee:
    employee_id: str
    title: str
    department_id: str
    manager_id: str
    status: str = "AVAILABLE"
    skills: tuple[str, ...] = ()
    current_task_id: str | None = None
    completed_tasks: int = 0
    failed_tasks: int = 0


@dataclass
class Manager:
    manager_id: str
    title: str
    parent_id: str
    department_id: str
    employee_ids: list[str] = field(default_factory=list)
    child_manager_ids: list[str] = field(default_factory=list)


@dataclass
class Department:
    department_id: str
    name: str
    manager_id: str


@dataclass
class Task:
    task_id: str
    objective: str
    status: str
    assigned_to: str | None = None
    manager_id: str | None = None
    department_id: str | None = None
    escalation_path: list[str] = field(default_factory=list)
    result: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time)


class EmployeeHierarchy:
    """Central registry and dispatcher for a scalable agent organization."""

    ROOT_ID = "BRAIN-001"
    DEFAULT_DEPARTMENTS = (
        ("DEPT-001", "RESEARCH", "MGR-001"),
        ("DEPT-002", "PRODUCTION", "MGR-002"),
    )

    def __init__(self, *, initial_employees: int = 10) -> None:
        self.managers: dict[str, Manager] = {
            "MGR-001": Manager("MGR-001", "Research Manager", self.ROOT_ID, "DEPT-001"),
            "MGR-002": Manager("MGR-002", "Production Manager", self.ROOT_ID, "DEPT-002"),
        }
        self.departments: dict[str, Department] = {
            "DEPT-001": Department("DEPT-001", "RESEARCH", "MGR-001"),
            "DEPT-002": Department("DEPT-002", "PRODUCTION", "MGR-002"),
        }
        self.employees: dict[str, Employee] = {}
        self.tasks: dict[str, Task] = {}
        self._employee_seq = 0
        self._task_seq = 0
        self.add_employees(max(0, int(initial_employees)))

    def _next_employee_id(self) -> str:
        self._employee_seq += 1
        return f"EMP-{self._employee_seq:06d}"

    def _next_task_id(self) -> str:
        self._task_seq += 1
        return f"TASK-{self._task_seq:09d}"

    def add_employees(self, count: int, *, department_id: str | None = None) -> list[Employee]:
        if count < 0:
            raise ValueError("count must be non-negative")
        created: list[Employee] = []
        manager_ids = [department_id and self.departments[department_id].manager_id or "MGR-001",
                       department_id and self.departments[department_id].manager_id or "MGR-002"]
        for index in range(count):
            manager_id = manager_ids[index % len(manager_ids)]
            dept = self.managers[manager_id].department_id
            employee = Employee(
                employee_id=self._next_employee_id(),
                title="AI Employee",
                department_id=dept,
                manager_id=manager_id,
                skills=("general",),
            )
            self.employees[employee.employee_id] = employee
            self.managers[manager_id].employee_ids.append(employee.employee_id)
            created.append(employee)
        return created

    def add_manager(self, manager_id: str, title: str, parent_id: str = ROOT_ID,
                    department_id: str = "DEPT-001") -> Manager:
        if manager_id in self.managers:
            raise ValueError("manager_id already exists")
        if parent_id != self.ROOT_ID and parent_id not in self.managers:
            raise ValueError("parent manager does not exist")
        if department_id not in self.departments:
            raise ValueError("department does not exist")
        manager = Manager(manager_id, title, parent_id, department_id)
        self.managers[manager_id] = manager
        if parent_id != self.ROOT_ID:
            self.managers[parent_id].child_manager_ids.append(manager_id)
        return manager

    def assign_task(self, objective: str, *, department_id: str | None = None) -> Task:
        """Assign to an available employee; otherwise leave queued for the manager."""
        objective = str(objective).strip()
        if not objective:
            raise ValueError("objective is required")

        candidates = [
            e for e in self.employees.values()
            if e.status == "AVAILABLE" and (department_id is None or e.department_id == department_id)
        ]
        candidates.sort(key=lambda e: (e.completed_tasks, e.employee_id))
        task = Task(
            task_id=self._next_task_id(),
            objective=objective,
            status="QUEUED",
            department_id=department_id,
        )
        if candidates:
            employee = candidates[0]
            task.status = "ASSIGNED"
            task.assigned_to = employee.employee_id
            task.manager_id = employee.manager_id
            task.department_id = employee.department_id
            task.escalation_path = [employee.employee_id, employee.manager_id, self.ROOT_ID]
            employee.status = "BUSY"
            employee.current_task_id = task.task_id
        else:
            task.status = "MANAGER_REVIEW"
            task.manager_id = (
                self.departments[department_id].manager_id if department_id else "MGR-001"
            )
            task.escalation_path = [task.manager_id, self.ROOT_ID]
        self.tasks[task.task_id] = task
        return task

    def complete_task(self, task_id: str, *, success: bool, result: dict[str, Any] | None = None) -> Task:
        task = self.tasks[task_id]
        task.status = "COMPLETED" if success else "FAILED"
        task.result = dict(result or {})
        if task.assigned_to and task.assigned_to in self.employees:
            employee = self.employees[task.assigned_to]
            employee.status = "AVAILABLE"
            employee.current_task_id = None
            if success:
                employee.completed_tasks += 1
            else:
                employee.failed_tasks += 1
        return task

    def escalate(self, task_id: str) -> Task:
        task = self.tasks[task_id]
        task.status = "ESCALATED"
        if task.assigned_to and task.assigned_to in self.employees:
            employee = self.employees[task.assigned_to]
            employee.status = "AVAILABLE"
            employee.current_task_id = None
        task.assigned_to = None
        task.manager_id = self.managers[task.manager_id].parent_id if task.manager_id in self.managers else self.ROOT_ID
        task.escalation_path = task.escalation_path + [task.manager_id]
        return task

    def snapshot(self) -> dict[str, Any]:
        return {
            "root_manager": self.ROOT_ID,
            "employee_count": len(self.employees),
            "manager_count": len(self.managers),
            "department_count": len(self.departments),
            "employees": [asdict(x) for x in self.employees.values()],
            "managers": [asdict(x) for x in self.managers.values()],
            "departments": [asdict(x) for x in self.departments.values()],
            "tasks": [asdict(x) for x in self.tasks.values()],
            "scalable": True,
            "money_movement": False,
            "permission_granting": False,
        }
