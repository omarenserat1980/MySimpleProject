"""Continuous goal generation for Brain V7.

Generates the next bounded objective from the current state and keeps rotating
through research, revenue, creation, validation, learning, and reliability.
Goals are planning artifacts; they do not grant permissions or imply income.
"""
from __future__ import annotations

from dataclasses import dataclass
import time


@dataclass(frozen=True)
class Goal:
    goal_id: str
    title: str
    purpose: str
    priority: int
    created_at: float


GOAL_TEMPLATES = (
    ("research", "ابحث عن فرص ربح مشروعة جديدة موثقة", "increase verified opportunity flow"),
    ("qualify", "صفِّ الفرص حسب الدليل والسرعة والاقتصاد", "reduce wasted execution time"),
    ("create", "أنشئ أصلًا رقميًا قابلًا للبيع من أفضل فرصة", "increase reusable output"),
    ("validate", "تحقق من جودة الأصل والطلب والقيود", "prevent unsupported claims"),
    ("learn", "حلل نتائج الدورات السابقة وحدّث الأولويات", "improve future decisions"),
    ("reliability", "افحص صحة النظام والتعافي والاستمرارية", "keep the runtime operational"),
)


def next_goal(cycle: int = 0, now: float | None = None) -> Goal:
    idx = max(0, cycle) % len(GOAL_TEMPLATES)
    key, title, purpose = GOAL_TEMPLATES[idx]
    return Goal(
        goal_id=f"{key}-{cycle + 1}",
        title=title,
        purpose=purpose,
        priority=100 - idx * 5,
        created_at=time.time() if now is None else now,
    )


def goal_snapshot(cycle: int, current_goal: Goal | None = None) -> dict:
    goal = current_goal or next_goal(cycle)
    return {
        "cycle": cycle,
        "current_goal": {
            "goal_id": goal.goal_id,
            "title": goal.title,
            "purpose": goal.purpose,
            "priority": goal.priority,
            "created_at": goal.created_at,
        },
        "continuous_generation": True,
        "next_goal_generated": True,
    }
