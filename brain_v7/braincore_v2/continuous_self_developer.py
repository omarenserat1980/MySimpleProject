"""Continuous self-development supervisor for Brain V7.

Plans bounded development iterations continuously. Each iteration must produce
evidence before promotion. Protected financial/legal/security areas remain
subject to their existing safety and authorization gates.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import time

from .autonomous_development_supervisor import DevelopmentTask


@dataclass(frozen=True)
class DevelopmentCycle:
    iteration: int
    task_id: str
    objective: str
    status: str
    evidence_required: bool = True
    created_at: float = 0.0


def next_development_cycle(iteration: int) -> DevelopmentCycle:
    task = DevelopmentTask(
        task_id=f"continuous-{iteration}",
        domain="software_engineering",
        objective="تحسين القدرة التالية القابلة للقياس مع اختبار ودليل",
        reason="continuous self-development",
        risk="bounded",
    )
    return DevelopmentCycle(
        iteration=iteration,
        task_id=task.task_id,
        objective=task.objective,
        status="PLANNED",
        created_at=time.time(),
    )


def promote_cycle(cycle: DevelopmentCycle, *, tests_passed: bool,
                  evidence: str) -> DevelopmentCycle:
    if not tests_passed or not evidence.strip():
        return DevelopmentCycle(
            **{**asdict(cycle), "status": "BLOCKED_NO_EVIDENCE"}
        )
    return DevelopmentCycle(
        **{**asdict(cycle), "status": "PROMOTED"}
    )


def supervisor_snapshot(iteration: int) -> dict:
    cycle = next_development_cycle(max(1, iteration))
    return {
        "continuous_self_development": True,
        "cycle": asdict(cycle),
        "requires_tests_and_evidence": True,
        "unrestricted_self_modification": False,
        "external_side_effects": False,
    }
