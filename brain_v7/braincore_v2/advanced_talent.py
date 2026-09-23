"""Advanced workforce development: mentoring, rotation, certification, and knowledge transfer."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from .employee_hierarchy import EmployeeHierarchy, Employee

@dataclass
class TalentRecord:
    employee_id: str
    mentor_id: str | None = None
    certifications: set[str] = field(default_factory=set)
    rotations: list[str] = field(default_factory=list)
    knowledge_contributions: int = 0
    coaching_count: int = 0
    readiness: float = 0.0

class AdvancedTalentEngine:
    """Evidence-driven employee growth beyond basic performance reviews."""
    def __init__(self, organization: EmployeeHierarchy) -> None:
        self.organization = organization
        self.records: dict[str, TalentRecord] = {
            e.employee_id: TalentRecord(e.employee_id)
            for e in organization.employees.values()
        }

    def sync(self) -> None:
        for e in self.organization.employees.values():
            self.records.setdefault(e.employee_id, TalentRecord(e.employee_id))

    def select_mentor(self, employee_id: str) -> str | None:
        self.sync()
        target = self.organization.employees.get(employee_id)
        if not target:
            return None
        candidates = [
            e for e in self.organization.employees.values()
            if e.employee_id != employee_id and e.status != "RETIRED"
            and e.department_id == target.department_id
            and (e.completed_tasks >= 5 or e.title.lower().find("manager") >= 0)
        ]
        candidates.sort(key=lambda e: (-e.completed_tasks, -len(e.competency_scores), e.employee_id))
        mentor = candidates[0] if candidates else None
        if mentor:
            self.records[employee_id].mentor_id = mentor.employee_id
            self.records[mentor.employee_id].coaching_count += 1
        return mentor.employee_id if mentor else None

    def certify(self, employee_id: str, certification: str) -> dict[str, Any]:
        self.sync()
        e = self.organization.employees[employee_id]
        avg = (sum(e.competency_scores.values()) / len(e.competency_scores)) if e.competency_scores else 0
        if avg >= 75 and e.completed_tasks >= 5:
            self.records[employee_id].certifications.add(certification)
            return {"employee_id": employee_id, "certified": True, "certification": certification}
        return {"employee_id": employee_id, "certified": False, "reason": "insufficient demonstrated competency"}

    def propose_rotation(self, employee_id: str) -> dict[str, Any]:
        self.sync()
        e = self.organization.employees[employee_id]
        departments = [d for d in self.organization.departments if d != e.department_id]
        if not departments:
            return {"employee_id": employee_id, "rotation": None}
        target = departments[hash(employee_id) % len(departments)]
        self.records[employee_id].rotations.append(target)
        return {"employee_id": employee_id, "rotation": target, "status": "PROPOSED"}

    def readiness_score(self, employee_id: str) -> float:
        self.sync()
        e = self.organization.employees[employee_id]
        total = e.completed_tasks + e.failed_tasks
        success = e.completed_tasks / total if total else 0
        competency = (sum(e.competency_scores.values()) / len(e.competency_scores) / 100) if e.competency_scores else 0
        net = max(0.0, e.revenue_generated - e.costs_attributed)
        financial = net / (net + 1000) if net else 0
        training = min(e.training_completed / 10, 1)
        coaching = min(self.records[employee_id].coaching_count / 5, 1)
        score = success*.25 + competency*.25 + financial*.25 + training*.15 + coaching*.10
        self.records[employee_id].readiness = round(score, 4)
        return self.records[employee_id].readiness

    def develop(self, employee_id: str) -> dict[str, Any]:
        mentor = self.select_mentor(employee_id)
        readiness = self.readiness_score(employee_id)
        e = self.organization.employees[employee_id]
        return {
            "employee_id": employee_id,
            "mentor_id": mentor,
            "readiness": readiness,
            "certifications": sorted(self.records[employee_id].certifications),
            "rotations": list(self.records[employee_id].rotations),
            "development_actions": list(e.development_plan),
        }

    def organization_snapshot(self) -> dict[str, Any]:
        self.sync()
        active = [e for e in self.organization.employees.values() if e.status != "RETIRED"]
        ranked = sorted(
            [{"employee_id": e.employee_id, "readiness": self.readiness_score(e.employee_id)}
             for e in active],
            key=lambda x: (-x["readiness"], x["employee_id"])
        )
        return {"active": len(active), "talent_readiness_ranking": ranked}
