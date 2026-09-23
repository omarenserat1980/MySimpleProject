"""Bounded V1..V100 evolution planner for the electronic brain.

Each generation proposes the next engineering improvement from measurable
gaps. It does not self-grant permissions, deploy code, submit jobs, or move
money. Progress requires evidence.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable


@dataclass(frozen=True)
class EvolutionStep:
    generation: int
    objective: str
    expected_gain: str
    evidence_required: str
    side_effects_allowed: bool = False


OBJECTIVES = (
    ("opportunity_discovery", "زيادة مصادر الفرص الموثوقة", "مصادر حديثة قابلة للتحقق"),
    ("qualification", "تحسين فلترة الفرص", "دقة أعلى في الاستبعاد والتأهيل"),
    ("artifact_factory", "تسريع إنتاج المنتجات الرقمية", "أثر نهائي قابل للفحص"),
    ("api_delivery", "تحسين مسارات التسليم عبر API", "اتصال ومصادقة وصلاحية مثبتة"),
    ("reuse", "إعادة استخدام الأصول", "انخفاض زمن الإنتاج"),
    ("experimentation", "اختبارات اقتصادية أسرع", "نتيجة موثقة قبل التوسع"),
    ("learning", "تعلم من النتائج", "أدلة نتائج موثقة"),
    ("risk", "تقليل المخاطر", "اختبارات فشل وتمرير"),
    ("reliability", "رفع الاعتمادية", "اختبارات ناجحة قابلة للتكرار"),
    ("orchestration", "دمج دورة الفرصة كاملة", "سجل دورة مكتمل"),
)


def evolution_plan(start: int = 1, end: int = 100) -> list[dict]:
    if not (1 <= start <= end <= 100):
        raise ValueError("generation range must be within 1..100")
    steps = []
    for generation in range(start, end + 1):
        key, objective, evidence = OBJECTIVES[(generation - 1) % len(OBJECTIVES)]
        steps.append(asdict(EvolutionStep(
            generation=generation,
            objective=f"{key}: {objective}",
            expected_gain="زيادة القدرة القابلة للقياس، لا ادعاء ربح مضمون",
            evidence_required=evidence,
        )))
    return steps


def next_step(completed: Iterable[int] = ()) -> dict:
    done = {int(x) for x in completed if 1 <= int(x) <= 100}
    for step in evolution_plan():
        if step["generation"] not in done:
            return step
    return {"status": "V100_COMPLETE", "next": None}


def verify_progress(generation: int, passed: bool, evidence: str = "") -> dict:
    if generation < 1 or generation > 100:
        raise ValueError("generation must be within 1..100")
    if not passed or not evidence.strip():
        return {
            "status": "BLOCKED",
            "generation": generation,
            "reason": "EVIDENCE_REQUIRED",
        }
    return {
        "status": "VERIFIED",
        "generation": generation,
        "evidence": evidence.strip(),
        "next_generation": generation + 1 if generation < 100 else None,
    }


def snapshot(completed: Iterable[int] = ()) -> dict:
    done = sorted({int(x) for x in completed if 1 <= int(x) <= 100})
    return {
        "target": 100,
        "completed": done,
        "completed_count": len(done),
        "remaining": 100 - len(done),
        "continuous_mode": True,
        "requires_evidence": True,
        "autonomous_side_effects": False,
    }
