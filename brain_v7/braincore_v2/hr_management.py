"""HR management primitives for the Electronic Brain workforce.

Applies standard HR ideas: competency matrices, goals, performance reviews,
development plans, succession readiness, recognition and fair retention rules.
It is a software workforce model; it does not infer human mental states.
"""
from __future__ import annotations

from dataclasses import asdict
from time import time
from typing import Any

from .employee_hierarchy import EmployeeHierarchy


class HRManagementEngine:
    def __init__(self, organization: EmployeeHierarchy) -> None:
        self.organization = organization

    def competency_matrix(self) -> list[dict[str, Any]]:
        rows = []
        for e in self.organization.employees.values():
            rows.append({
                "employee_id": e.employee_id,
                "title": e.title,
                "department_id": e.department_id,
                "competencies": dict(e.competency_scores),
                "goals": list(e.goals),
                "development_plan": list(e.development_plan),
            })
        return rows

    def set_competency(self, employee_id: str, skill: str, score: float) -> dict[str, Any]:
        employee = self.organization.employees[employee_id]
        employee.competency_scores[str(skill)] = max(0.0, min(100.0, float(score)))
        return {"employee_id": employee_id, "skill": skill, "score": employee.competency_scores[skill]}

    def set_goals(self, employee_id: str, goals: list[str]) -> dict[str, Any]:
        employee = self.organization.employees[employee_id]
        employee.goals = [str(g).strip() for g in goals if str(g).strip()]
        return {"employee_id": employee_id, "goals": employee.goals}

    def build_development_plan(self, employee_id: str) -> dict[str, Any]:
        employee = self.organization.employees[employee_id]
        gaps = [skill for skill, score in employee.competency_scores.items() if score < 70]
        employee.development_plan = [f"Improve {skill}" for skill in gaps]
        return {"employee_id": employee_id, "development_plan": employee.development_plan}

    def performance_review(self, employee_id: str) -> dict[str, Any]:
        employee = self.organization.employees[employee_id]
        total = employee.completed_tasks + employee.failed_tasks
        task_success = employee.completed_tasks / total if total else 0.5
        competency = (
            sum(employee.competency_scores.values()) / len(employee.competency_scores) / 100
            if employee.competency_scores else 0.5
        )
        score = round(
            task_success * 0.35
            + competency * 0.20
            + employee.attendance_score * 0.10
            + employee.collaboration_score * 0.10
            + min(employee.training_completed / 10.0, 1.0) * 0.10
            + min(max(employee.revenue_generated - employee.costs_attributed, 0.0) / 1000.0, 1.0) * 0.15,
            4,
        )
        employee.last_review_at = time()
        return {
            "employee_id": employee_id,
            "review_score": score,
            "task_success": round(task_success, 4),
            "competency": round(competency, 4),
            "net_value": round(employee.revenue_generated - employee.costs_attributed, 2),
            "development_plan": list(employee.development_plan),
        }

    def workforce_dashboard(self) -> dict[str, Any]:
        active = [e for e in self.organization.employees.values() if e.status != "RETIRED"]
        return {
            "active_employees": len(active),
            "retired_employees": sum(e.status == "RETIRED" for e in self.organization.employees.values()),
            "training_ready": sum(bool(e.development_plan) for e in active),
            "average_competency": round(
                sum(
                    (sum(e.competency_scores.values()) / len(e.competency_scores))
                    if e.competency_scores else 0.0
                    for e in active
                ) / len(active), 2
            ) if active else 0.0,
            "succession_ready": sum(
                e.completed_tasks >= 12 and e.status != "RETIRED"
                for e in active
            ),
        }
