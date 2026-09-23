"""Evidence-based internal revenue challenge.

A 10,000 JOD target is treated as a goal, not guaranteed income. Only
verified, legitimate realized revenue counts; costs are tracked separately.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

@dataclass
class RevenueEntry:
    employee_id: str
    amount_jod: float
    verified: bool = False
    evidence: str | None = None

class RevenueChallenge:
    TARGET_JOD = 10_000.0

    def __init__(self, organization) -> None:
        self.organization = organization
        self.entries: list[RevenueEntry] = []
        self.status = "ACTIVE"

    def record(self, employee_id: str, amount_jod: float,
               verified: bool = False, evidence: str | None = None) -> dict[str, Any]:
        if employee_id not in self.organization.employees:
            raise KeyError(employee_id)
        amount = max(0.0, float(amount_jod))
        entry = RevenueEntry(employee_id, amount, verified, evidence)
        self.entries.append(entry)
        return entry.__dict__

    def leaderboard(self) -> list[dict[str, Any]]:
        totals: dict[str, float] = {}
        for e in self.entries:
            if e.verified:
                totals[e.employee_id] = totals.get(e.employee_id, 0.0) + e.amount_jod
        rows = [{"employee_id": k, "verified_revenue_jod": round(v, 2)}
                for k, v in totals.items()]
        return sorted(rows, key=lambda x: (-x["verified_revenue_jod"], x["employee_id"]))

    def progress(self) -> dict[str, Any]:
        total = sum(e.amount_jod for e in self.entries if e.verified)
        return {
            "target_jod": self.TARGET_JOD,
            "verified_revenue_jod": round(total, 2),
            "remaining_jod": round(max(0.0, self.TARGET_JOD - total), 2),
            "progress": round(min(1.0, total / self.TARGET_JOD), 4),
            "status": "TARGET_REACHED" if total >= self.TARGET_JOD else "IN_PROGRESS",
            "leaderboard": self.leaderboard(),
        }

    def snapshot(self) -> dict[str, Any]:
        return {"challenge": "10,000 JOD", **self.progress(),
                "entries": [e.__dict__ for e in self.entries[-200:]]}
