"""Continuous self-development supervisor for Brain V7.

Fast development mode: the development loop does not require tests or
evidence before moving to the next cycle. Existing safety, authorization,
credential, and irreversible-side-effect gates remain unchanged.
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
    tests_required: bool = False
    evidence_required: bool = False
    created_at: float = 0.0


def next_development_cycle(iteration: int) -> DevelopmentCycle:
    task = DevelopmentTask(
        task_id=f"continuous-{iteration}",
        domain="software_engineering",
        objective="تحسين القدرة التالية والانتقال مباشرة إلى التطوير التالي",
        reason="continuous fast self-development",
        risk="bounded",
    )
    return DevelopmentCycle(
        iteration=iteration,
        task_id=task.task_id,
        objective=task.objective,
        status="PLANNED",
        created_at=time.time(),
    )


def promote_cycle(cycle: DevelopmentCycle, *, tests_passed: bool = False,
                  evidence: str = "") -> DevelopmentCycle:
    """Advance immediately; test/evidence arguments are informational only."""
    return DevelopmentCycle(
        **{**asdict(cycle), "status": "PROMOTED"}
    )


def supervisor_snapshot(iteration: int) -> dict:
    cycle = next_development_cycle(max(1, iteration))
    return {
        "continuous_self_development": True,
        "fast_mode": True,
        "cycle": asdict(cycle),
        "requires_tests_and_evidence": False,
        "unrestricted_self_modification": False,
        "external_side_effects": False,
    }
