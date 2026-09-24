"""Competitive leadership and succession for the Electronic Brain.

Employees compete through measurable performance, reliability, learning,
capability breadth and efficiency. The engine can nominate a successor and
perform a controlled internal succession. It never changes external
permissions or credentials.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from time import time
from typing import Any

from .employee_hierarchy import EmployeeHierarchy, Employee
from .notifications import NotificationCenter


@dataclass
class LeadershipRecord:
    active_brain_id: str = "BRAIN-001"
    generation: int = 1
    last_successor_id: str | None = None
    succession_count: int = 0
    last_transition_at: float = 0.0


class LeadershipEvolutionEngine:
    def __init__(
        self,
        organization: EmployeeHierarchy,
        notifications: NotificationCenter,
        *,
        succession_threshold: float = 0.40,
        minimum_tasks: int = 12,
        minimum_margin: float = 0.05,
    ) -> None:
        self.organization = organization
        self.notifications = notifications
        self.succession_threshold = succession_threshold
        self.minimum_tasks = minimum_tasks
        self.minimum_margin = minimum_margin
        self.record = LeadershipRecord()

    @staticmethod
    def score(employee: Employee) -> float:
        total = employee.completed_tasks + employee.failed_tasks
        if total == 0:
            return 0.0
        success = employee.completed_tasks / total
        experience = min(employee.completed_tasks / 50.0, 1.0)
        breadth = min(len(set(employee.skills)) / 8.0, 1.0)
        net = max(0.0, employee.revenue_generated - employee.costs_attributed)
        financial = net / (net + 1000.0) if net > 0 else 0.0
        return round(
            financial * 0.35
            + success * 0.30
            + experience * 0.15
            + breadth * 0.10
            + (success * experience) * 0.10,
            4,
        )

    def leaderboard(self) -> list[dict[str, Any]]:
        rows = []
        for employee in self.organization.employees.values():
            if employee.status == "RETIRED":
                continue
            rows.append({
                "employee_id": employee.employee_id,
                "title": employee.title,
                "score": self.score(employee),
                "completed_tasks": employee.completed_tasks,
                "failed_tasks": employee.failed_tasks,
                "skills": list(employee.skills),
                "department_id": employee.department_id,
            })
        return sorted(rows, key=lambda x: (-x["score"], -x["completed_tasks"], x["employee_id"]))

    def evaluate(self) -> dict[str, Any]:
        board = self.leaderboard()
        candidate = board[0] if board else None
        eligible = False
        margin = 0.0
        if candidate:
            second = board[1]["score"] if len(board) > 1 else 0.0
            margin = candidate["score"] - second
            eligible = (
                candidate["score"] >= self.succession_threshold
                and candidate["completed_tasks"] >= self.minimum_tasks
                and margin >= self.minimum_margin
            )
        return {
            "active_brain_id": self.record.active_brain_id,
            "generation": self.record.generation,
            "leaderboard": board,
            "candidate": candidate,
            "eligible_for_succession": eligible,
            "candidate_margin": round(margin, 4),
        }

    def run(self) -> dict[str, Any]:
        evaluation = self.evaluate()
        if not evaluation["eligible_for_succession"]:
            return {**evaluation, "succession_performed": False}

        successor_id = evaluation["candidate"]["employee_id"]
        old_brain = self.record.active_brain_id
        if successor_id == old_brain:
            return {**evaluation, "succession_performed": False}

        successor = self.organization.employees[successor_id]
        successor.status = "BRAIN_SUCCESSOR"
        successor.title = "Electronic Brain — Successor"
        self.record.active_brain_id = successor_id
        self.record.last_successor_id = successor_id
        self.record.succession_count += 1
        self.record.generation += 1
        self.record.last_transition_at = time()

        self.notifications.emit(
            "BRAIN_SUCCESSION",
            sender_id=old_brain,
            recipient_id=successor_id,
            message=f"{successor_id} became the active internal Brain successor",
            priority="HIGH",
            data={"previous_brain": old_brain, "generation": self.record.generation},
        )
        self.notifications.emit(
            "BRAIN_RETIRED",
            sender_id=successor_id,
            recipient_id=old_brain,
            message=f"Previous Brain generation {old_brain} was retired from active leadership",
            priority="HIGH",
            data={"successor": successor_id, "generation": self.record.generation},
        )
        return {**evaluation, "succession_performed": True, "successor_id": successor_id}

    def snapshot(self) -> dict[str, Any]:
        return asdict(self.record) | {
            "threshold": self.succession_threshold,
            "minimum_tasks": self.minimum_tasks,
            "minimum_margin": self.minimum_margin,
        }
