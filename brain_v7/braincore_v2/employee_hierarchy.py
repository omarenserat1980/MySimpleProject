"""Scalable organizational hierarchy for the Electronic Brain.

The Brain is the general manager. Under it are departments, department
managers, and specialized AI employees. This is an organizational/routing
layer only; it does not grant financial, credential, legal, or irreversible
external permissions.
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
    revenue_generated: float = 0.0
    costs_attributed: float = 0.0
    training_completed: int = 0
    competency_scores: dict[str, float] = field(default_factory=dict)
    goals: list[str] = field(default_factory=list)
    development_plan: list[str] = field(default_factory=list)
    last_review_at: float | None = None
    attendance_score: float = 1.0
    collaboration_score: float = 0.5
    wellbeing_flag: bool = False


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


# Initial operating model: 11 departments, 11 managers, 53 specialists = 64
# AI workers beneath the Brain. The counts are a starting capacity, not a
# hard limit; the registry can scale further.
DEFAULT_STAFFING_PLAN: tuple[tuple[str, str, tuple[tuple[str, tuple[str, ...]], ...]], ...] = (
    ("DEPT-001", "EXECUTIVE_OPERATIONS", (
        ("Chief of Staff", ("coordination", "prioritization")),
        ("Strategic Planner", ("planning", "objectives")),
        ("Resource Coordinator", ("allocation", "scheduling")),
    )),
    ("DEPT-002", "RESEARCH_INTELLIGENCE", (
        ("Opportunity Researcher", ("research", "opportunity_discovery")),
        ("Market Analyst", ("market_analysis", "competition")),
        ("Source Verifier", ("verification", "evidence")),
        ("Trend Analyst", ("trends", "forecasting")),
        ("Research Assistant", ("research", "data_collection")),
    )),
    ("DEPT-003", "FINANCE_ECONOMICS", (
        ("Financial Analyst", ("unit_economics", "profitability")),
        ("Revenue Analyst", ("revenue", "forecasting")),
        ("Cost Analyst", ("costs", "budgets")),
        ("Reconciliation Specialist", ("reconciliation", "payment_evidence")),
    )),
    ("DEPT-004", "ENGINEERING_TECHNOLOGY", (
        ("Software Engineer", ("python", "software")),
        ("AI Engineer", ("ai", "agents")),
        ("Automation Engineer", ("automation", "workflows")),
        ("Backend Engineer", ("apis", "backend")),
        ("Data Engineer", ("data", "pipelines")),
        ("Infrastructure Engineer", ("cloud", "deployment")),
        ("Testing Engineer", ("testing", "verification")),
        ("Integration Engineer", ("integrations", "providers")),
    )),
    ("DEPT-005", "MEDIA_PRODUCTION", (
        ("Creative Director", ("creative_direction", "story")),
        ("Script Writer", ("script", "storytelling")),
        ("Cinematic Producer", ("cinematic", "production")),
        ("Video Editor", ("editing", "video")),
        ("Audio Specialist", ("audio", "voice")),
        ("Visual Designer", ("design", "visuals")),
        ("Media Quality Specialist", ("media_quality", "continuity")),
    )),
    ("DEPT-006", "MARKETING_SALES", (
        ("Marketing Strategist", ("marketing", "strategy")),
        ("Content Marketer", ("content", "social_media")),
        ("Sales Researcher", ("sales", "lead_research")),
        ("Offer Specialist", ("offers", "proposals")),
        ("Customer Insights Analyst", ("customers", "feedback")),
    )),
    ("DEPT-007", "OPERATIONS_DELIVERY", (
        ("Operations Manager Assistant", ("operations", "workflow")),
        ("Task Dispatcher", ("dispatch", "queue")),
        ("Delivery Coordinator", ("delivery", "deadlines")),
        ("Process Optimizer", ("optimization", "process")),
        ("Operations Analyst", ("operations", "metrics")),
    )),
    ("DEPT-008", "SECURITY_GOVERNANCE", (
        ("Security Analyst", ("security", "threats")),
        ("Permission Auditor", ("permissions", "access_control")),
        ("Risk Analyst", ("risk", "risk_management")),
        ("Audit Specialist", ("audit", "audit_chain")),
    )),
    ("DEPT-009", "QUALITY_COMPLIANCE", (
        ("Quality Assurance Analyst", ("quality", "acceptance")),
        ("Compliance Analyst", ("compliance", "policy")),
        ("Fact Checker", ("fact_checking", "evidence")),
        ("Release Reviewer", ("release", "final_review")),
    )),
    ("DEPT-010", "LEARNING_DEVELOPMENT", (
        ("Learning Analyst", ("learning", "evidence")),
        ("Capability Planner", ("capabilities", "skill_gaps")),
        ("Performance Analyst", ("performance", "metrics")),
        ("Development Engineer", ("self_development", "improvement")),
    )),
    ("DEPT-011", "DATA_ANALYTICS", (
        ("Data Analyst", ("analytics", "statistics")),
        ("Metrics Engineer", ("metrics", "measurement")),
        ("Experiment Analyst", ("experiments", "evaluation")),
        ("Knowledge Analyst", ("knowledge", "memory")),
    )),
)


class EmployeeHierarchy:
    """Central registry, staffing plan, dispatcher, and escalation chain."""

    ROOT_ID = "BRAIN-001"

    def __init__(self, *, initial_employees: int | None = None) -> None:
        self.managers: dict[str, Manager] = {}
        self.departments: dict[str, Department] = {}
        self.employees: dict[str, Employee] = {}
        self.tasks: dict[str, Task] = {}
        self._employee_seq = 0
        self._task_seq = 0
        self._build_departments_and_managers()

        if initial_employees is None:
            self.build_full_staffing()
        else:
            self.add_employees(max(0, int(initial_employees)))

    def _build_departments_and_managers(self) -> None:
        for index, (department_id, name, _roles) in enumerate(DEFAULT_STAFFING_PLAN, start=1):
            manager_id = f"MGR-{index:03d}"
            self.departments[department_id] = Department(department_id, name, manager_id)
            self.managers[manager_id] = Manager(
                manager_id, f"{name.title().replace('_', ' ')} Manager",
                self.ROOT_ID, department_id
            )

    def _next_employee_id(self) -> str:
        self._employee_seq += 1
        return f"EMP-{self._employee_seq:06d}"

    def _next_task_id(self) -> str:
        self._task_seq += 1
        return f"TASK-{self._task_seq:09d}"

    def build_full_staffing(self) -> list[Employee]:
        """Create the planned specialists for every department."""
        created: list[Employee] = []
        for department_id, _name, roles in DEFAULT_STAFFING_PLAN:
            manager_id = self.departments[department_id].manager_id
            for title, skills in roles:
                employee = Employee(
                    employee_id=self._next_employee_id(),
                    title=title,
                    department_id=department_id,
                    manager_id=manager_id,
                    skills=skills,
                )
                self.employees[employee.employee_id] = employee
                self.managers[manager_id].employee_ids.append(employee.employee_id)
                created.append(employee)
        return created

    def add_employees(
        self,
        count: int,
        *,
        department_id: str | None = None,
        title: str = "AI Employee",
        skills: tuple[str, ...] = ("general",),
    ) -> list[Employee]:
        if count < 0:
            raise ValueError("count must be non-negative")
        if department_id is not None and department_id not in self.departments:
            raise ValueError("department does not exist")
        manager_ids = (
            [self.departments[department_id].manager_id]
            if department_id
            else list(self.managers)
        )
        created: list[Employee] = []
        for index in range(count):
            manager_id = manager_ids[index % len(manager_ids)]
            dept = self.managers[manager_id].department_id
            employee = Employee(
                employee_id=self._next_employee_id(),
                title=title,
                department_id=dept,
                manager_id=manager_id,
                skills=skills,
            )
            self.employees[employee.employee_id] = employee
            self.managers[manager_id].employee_ids.append(employee.employee_id)
            created.append(employee)
        return created

    def add_manager(
        self, manager_id: str, title: str, parent_id: str = ROOT_ID,
        department_id: str = "DEPT-001"
    ) -> Manager:
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
        objective = str(objective).strip()
        if not objective:
            raise ValueError("objective is required")

        candidates = [
            e for e in self.employees.values()
            if e.status == "AVAILABLE"
            and (department_id is None or e.department_id == department_id)
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
                self.departments[department_id].manager_id
                if department_id else next(iter(self.managers), self.ROOT_ID)
            )
            task.escalation_path = [task.manager_id, self.ROOT_ID]
        self.tasks[task.task_id] = task
        return task

    def complete_task(
        self, task_id: str, *, success: bool, result: dict[str, Any] | None = None
    ) -> Task:
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
        current_manager = task.manager_id
        if current_manager in self.managers:
            parent = self.managers[current_manager].parent_id
            task.manager_id = parent
        else:
            task.manager_id = self.ROOT_ID
        task.escalation_path = task.escalation_path + [task.manager_id]
        return task

    def ensure_team(
        self,
        *,
        department_id: str,
        name: str,
        manager_id: str,
        manager_title: str,
        roles: tuple[tuple[str, tuple[str, ...]], ...],
        goal: str,
    ) -> dict[str, Any]:
        """Idempotently create a named specialist team under the Brain."""
        if department_id not in self.departments:
            self.departments[department_id] = Department(department_id, name, manager_id)
        if manager_id not in self.managers:
            self.managers[manager_id] = Manager(
                manager_id, manager_title, self.ROOT_ID, department_id
            )
        existing_titles = {
            self.employees[e].title
            for e in self.managers[manager_id].employee_ids
            if e in self.employees
        }
        created: list[Employee] = []
        for title, skills in roles:
            if title in existing_titles:
                continue
            employee = Employee(
                employee_id=self._next_employee_id(),
                title=title,
                department_id=department_id,
                manager_id=manager_id,
                skills=skills,
                goals=[goal],
                development_plan=["plan", "produce", "review", "measure", "improve"],
            )
            self.employees[employee.employee_id] = employee
            self.managers[manager_id].employee_ids.append(employee.employee_id)
            created.append(employee)
        return {
            "department_id": department_id,
            "manager_id": manager_id,
            "employee_ids": list(self.managers[manager_id].employee_ids),
            "created": [asdict(e) for e in created],
            "goal": goal,
        }

    def ensure_specialized_team(
        self,
        *,
        department_id: str = "DEPT-CODE-TOOL",
        name: str = "CODE_TOOL_ENGINEERING",
        roles: tuple[tuple[str, tuple[str, ...]], ...] = (
            ("Code Tool Architect", ("code_tool_architecture", "python", "design")),
            ("Code Tool Developer", ("code_tool_development", "python", "refactoring")),
            ("Code Tool Test Engineer", ("testing", "pytest", "verification")),
            ("Code Tool Safety Engineer", ("sandbox", "permissions", "rollback")),
            ("Code Tool Repository Engineer", ("repository", "versioning", "snapshots")),
            ("Code Tool Automation Engineer", ("automation", "workflows", "orchestration")),
            ("Code Tool Performance Engineer", ("performance", "profiling", "optimization")),
            ("Code Tool QA Reviewer", ("quality", "review", "regression")),
        ),
    ) -> dict[str, Any]:
        """Create the permanent team dedicated exclusively to the Brain's coding tool.

        This team is a software-development workforce layer. It has no extra
        financial, credential, legal, or external-publication permissions.
        Calling the method repeatedly is idempotent.
        """
        if department_id not in self.departments:
            manager_id = "MGR-CODE-TOOL"
            self.departments[department_id] = Department(department_id, name, manager_id)
            self.managers[manager_id] = Manager(
                manager_id,
                "Code Tool Engineering Manager",
                self.ROOT_ID,
                department_id,
            )
        manager_id = self.departments[department_id].manager_id
        existing_titles = {self.employees[e].title for e in self.managers[manager_id].employee_ids}
        created: list[Employee] = []
        for title, skills in roles:
            if title in existing_titles:
                continue
            employee = Employee(
                employee_id=self._next_employee_id(),
                title=title,
                department_id=department_id,
                manager_id=manager_id,
                skills=skills,
                goals=["improve the Brain coding tool safely and continuously"],
                development_plan=["review", "test", "measure", "refine"],
            )
            self.employees[employee.employee_id] = employee
            self.managers[manager_id].employee_ids.append(employee.employee_id)
            created.append(employee)
        return {
            "department_id": department_id,
            "manager_id": manager_id,
            "employee_ids": list(self.managers[manager_id].employee_ids),
            "created": [asdict(e) for e in created],
            "specialization": "BRAIN_CODE_TOOL_ONLY",
        }

    def staffing_summary(self) -> dict[str, Any]:
        specialists = len(self.employees)
        managers = len(self.managers)
        return {
            "brain": self.ROOT_ID,
            "departments": len(self.departments),
            "department_managers": managers,
            "specialist_employees": specialists,
            "total_ai_workers_below_brain": managers + specialists,
            "planned_model": "11 department managers + 53 specialists",
            "scalable_beyond_plan": True,
        }

    def snapshot(self) -> dict[str, Any]:
        return {
            "root_manager": self.ROOT_ID,
            "employee_count": len(self.employees),
            "manager_count": len(self.managers),
            "department_count": len(self.departments),
            "staffing_summary": self.staffing_summary(),
            "employees": [asdict(x) for x in self.employees.values()],
            "managers": [asdict(x) for x in self.managers.values()],
            "departments": [asdict(x) for x in self.departments.values()],
            "tasks": [asdict(x) for x in self.tasks.values()],
            "scalable": True,
            "money_movement": False,
            "permission_granting": False,
        }
