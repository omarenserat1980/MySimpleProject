"""Revenue opportunity task factory.

Creates diversified, lawful revenue experiments for the workforce. It records
targets and verification requirements; it does not claim revenue until a real
transaction is independently verified.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass
class RevenueTask:
    task_id: str
    category: str
    objective: str
    success_metric: str
    verification: str
    risk: str = "LOW"

class RevenueTaskFactory:
    CATEGORIES = (
        ("DIGITAL_SERVICES", "Find and qualify paying clients for web/software/automation services."),
        ("MEDIA", "Produce original short-form/cinematic content packages for paying clients."),
        ("MARKETING", "Build measurable content/advertising services for businesses with authorized accounts."),
        ("RESEARCH", "Sell legitimate research, market-analysis, data-cleaning, or reporting services."),
        ("E_COMMERCE", "Identify products with lawful supplier access and validate demand before spending."),
        ("AFFILIATE", "Find legitimate affiliate programs and create original, compliant content."),
        ("TEMPLATES", "Create reusable digital templates, assets, or educational materials for sale."),
        ("LOCAL_SERVICES", "Identify local businesses that can pay for practical digital/operational services."),
    )

    def __init__(self) -> None:
        self.tasks: list[RevenueTask] = []
        self._counter = 0

    def generate(self, count: int = 8) -> list[dict[str, Any]]:
        count = max(1, min(50, int(count)))
        for i in range(count):
            category, objective = self.CATEGORIES[i % len(self.CATEGORIES)]
            self._counter += 1
            task = RevenueTask(
                task_id=f"REV-{self._counter:05d}",
                category=category,
                objective=objective,
                success_metric="Verified customer payment or platform payout",
                verification="Invoice/order/platform transaction + matching received amount",
            )
            self.tasks.append(task)
        return [t.__dict__ for t in self.tasks[-count:]]

    def prioritize(self) -> list[dict[str, Any]]:
        # Priority is based on low upfront cost, short validation cycle, and
        # direct path to a paying customer—not a prediction of profit.
        order = {
            "DIGITAL_SERVICES": 1, "LOCAL_SERVICES": 2, "RESEARCH": 3,
            "MEDIA": 4, "TEMPLATES": 5, "MARKETING": 6,
            "AFFILIATE": 7, "E_COMMERCE": 8,
        }
        return sorted([t.__dict__ for t in self.tasks],
                      key=lambda x: (order.get(x["category"], 99), x["task_id"]))

    def snapshot(self) -> dict[str, Any]:
        return {"task_count": len(self.tasks), "tasks": [t.__dict__ for t in self.tasks]}
