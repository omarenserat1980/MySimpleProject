"""Continuous self-development supervisor for Brain V7.

Fast mode: cycles advance without requiring tests or evidence. The supervisor
selects the next bounded engineering objective from the current capability
frontier. It plans concrete implementation work but does not grant new
permissions or bypass safety/credential/financial controls.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import time

from .autonomous_development_supervisor import DevelopmentTask
from .capability_registry import capability_summary


@dataclass(frozen=True)
class DevelopmentCycle:
    iteration: int
    task_id: str
    domain: str
    objective: str
    status: str
    tests_required: bool = False
    evidence_required: bool = False
    created_at: float = 0.0


DEVELOPMENT_FRONTIER = (
    ("software_engineering", "تحسين بنية الكود وتقليل التعقيد"),
    ("data_analysis", "تحسين تحليل البيانات واستخراج الإشارات المفيدة"),
    ("machine_learning", "إضافة قدرة تعلم آلي قابلة لإعادة الاستخدام"),
    ("ai_engineering", "تحسين قدرات الذكاء الاصطناعي والأتمتة المحلية"),
    ("autonomous_systems", "تحسين التخطيط والتنفيذ الذاتي المحلي"),
    ("operations", "تحسين الاستمرارية والتعافي والمراقبة"),
    ("marketing", "تحسين اكتشاف الطلب وصناعة العروض الرقمية"),
    ("sales", "تحسين تحويل الفرص إلى حزم قابلة للتقديم"),
    ("communication", "تحسين جودة النصوص والعروض العربية"),
    ("research", "تحسين البحث والفرز وتحديث الفرص"),
)


def _select_domain(iteration: int) -> tuple[str, str]:
    counts = capability_summary().get("counts", {})
    # Prefer the first frontier domain not yet marked as mastered.
    for domain, objective in DEVELOPMENT_FRONTIER:
        if counts.get(domain) != "MASTERED":
            return domain, objective
    return DEVELOPMENT_FRONTIER[(max(1, iteration) - 1) % len(DEVELOPMENT_FRONTIER)]


def next_development_cycle(iteration: int) -> DevelopmentCycle:
    domain, objective = _select_domain(iteration)
    task = DevelopmentTask(
        task_id=f"continuous-{iteration}",
        domain=domain,
        objective=objective,
        evidence="",
    )
    return DevelopmentCycle(
        iteration=iteration,
        task_id=task.task_id,
        domain=task.domain,
        objective=task.objective,
        status="PLANNED",
        created_at=time.time(),
    )


def implementation_plan(iteration: int) -> dict:
    cycle = next_development_cycle(max(1, iteration))
    return {
        "cycle": asdict(cycle),
        "actions": [
            "inspect_current_capability",
            "select_smallest_high_value_change",
            "implement_change",
            "save_checkpoint",
            "continue_to_next_cycle",
        ],
        "automatic_progression": True,
        "tests_required": False,
        "evidence_required": False,
        "external_side_effects": False,
    }


def promote_cycle(cycle: DevelopmentCycle, *, tests_passed: bool = False,
                  evidence: str = "") -> DevelopmentCycle:
    """Advance immediately; test/evidence arguments are informational only."""
    return DevelopmentCycle(**{**asdict(cycle), "status": "PROMOTED"})


def supervisor_snapshot(iteration: int) -> dict:
    plan = implementation_plan(max(1, iteration))
    return {
        "continuous_self_development": True,
        "fast_mode": True,
        "cycle": plan["cycle"],
        "implementation_plan": plan["actions"],
        "automatic_progression": True,
        "requires_tests_and_evidence": False,
        "unrestricted_self_modification": False,
        "external_side_effects": False,
    }
