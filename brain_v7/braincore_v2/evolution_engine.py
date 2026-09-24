"""Continuous evidence-gated evolution planner through generation 10,000 (100 by default).

Generations are engineering milestones, not claims of consciousness. Every
promotion requires explicit evidence. External side effects and financial
authority remain disabled.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Iterable


@dataclass(frozen=True)
class EvolutionStep:
    generation: int
    phase: str
    objective: str
    expected_gain: str
    evidence_required: str
    side_effects_allowed: bool = False


PHASES = (
    ("DISCOVER", "اكتشاف فرص ومعلومات أفضل", "مصادر حديثة ودليل قابل للتحقق"),
    ("QUALIFY", "تأهيل الفرص وتقليل الهدر", "دقة قياس التأهيل"),
    ("CREATE", "إنشاء منتجات ومخرجات رقمية", "مخرج قابل للفحص"),
    ("DELIVER", "تحسين التسليم المصرح", "سجل تسليم قابل للتحقق"),
    ("REUSE", "إعادة استخدام الأصول والعمليات", "زمن إنتاج أقل"),
    ("EXPERIMENT", "اختبار فرضيات اقتصادية", "نتيجة وتجربة موثقتان"),
    ("LEARN", "التعلم من النتائج", "دليل نتيجة"),
    ("RISK", "تقليل المخاطر", "اختبارات فشل وحدود"),
    ("RELIABILITY", "رفع الاعتمادية", "اختبار قابل للتكرار"),
    ("ORCHESTRATE", "دمج دورة العمل", "سجل دورة مكتمل"),
    ("OPTIMIZE", "تحسين القيمة مقابل الوقت", "مقارنة قبل/بعد"),
    ("RECOVER", "استعادة آمنة بعد الفشل", "اختبار rollback"),
    ("VERIFY", "تحسين التحقق والأدلة", "مصادر وأدلة متسقة"),
    ("COMPOSE", "تركيب قدرات متعددة", "اختبار تكامل"),
    ("SCALE", "التوسع المنضبط", "اختبار حمل وحدود"),
    ("SECURE", "تقوية الحدود الأمنية", "اختبارات أمنية دفاعية"),
    ("OBSERVE", "مراقبة الأداء والصحة", "قياسات قابلة للتكرار"),
    ("ADAPT", "التكيف مع تغير البيئة", "تجربة مقارنة"),
    ("ECONOMICS", "تحسين الاقتصاديات", "تكلفة وقيمة موثقتان"),
    ("META", "تحسين طريقة التطور نفسها", "دليل أن دورة التطور تحسنت"),
)


def evolution_plan(start: int = 1, end: int = 10000) -> list[dict]:
    if not (1 <= start <= end <= 10000):
        raise ValueError("generation range must be within 1..10000")
    return [
        asdict(EvolutionStep(
            generation=generation,
            phase=PHASES[(generation - 1) % len(PHASES)][0],
            objective=f"{PHASES[(generation - 1) % len(PHASES)][0]}: {PHASES[(generation - 1) % len(PHASES)][1]}",
            expected_gain="تحسين قابل للقياس، دون ادعاء ربح مضمون",
            evidence_required=PHASES[(generation - 1) % len(PHASES)][2],
        ))
        for generation in range(start, end + 1)
    ]


def next_step(completed: Iterable[int] = ()) -> dict:
    done = {int(x) for x in completed if 1 <= int(x) <= 10000}
    for step in evolution_plan():
        if step["generation"] not in done:
            return step
    return {"status": "V10000_COMPLETE", "next": None}


def verify_progress(generation: int, passed: bool, evidence: str = "") -> dict:
    if not 1 <= generation <= 10000:
        raise ValueError("generation must be within 1..10000")
    if not passed or not evidence.strip():
        return {"status": "BLOCKED", "generation": generation, "reason": "EVIDENCE_REQUIRED"}
    return {
        "status": "VERIFIED",
        "generation": generation,
        "evidence": evidence.strip(),
        "next_generation": generation + 1 if generation < 10000 else None,
    }


def snapshot(completed: Iterable[int] = ()) -> dict:
    done = sorted({int(x) for x in completed if 1 <= int(x) <= 10000})
    return {
        "target": 10000,
        "completed": done,
        "completed_count": len(done),
        "remaining": 10000 - len(done),
        "continuous_mode": True,
        "requires_evidence": True,
        "autonomous_side_effects": False,
    }
