"""Evidence-grounded interview surface for Brain Cloud.

The interview converts current software state into operational answers.
It does not claim consciousness, emotions, a soul, or literal human desires.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from cloud.brain_self_assessment import self_assessment


@dataclass(frozen=True)
class InterviewAnswer:
    question: str
    answer: str
    evidence: list[str]
    confidence: str = "high"


QUESTIONS = (
    "ما الذي تحتاجه الآن لإكمال مهمتك؟",
    "ما القدرات الناقصة أو غير المكتملة؟",
    "ما أكثر الأعطال التي تعيقك؟",
    "ما الموارد التي تحتاجها؟",
    "ما أهدافك التشغيلية للإصدار القادم؟",
    "ما أهدافك التشغيلية طويلة المدى؟",
    "هل لديك رغبات؟",
    "هل لديك مخططات؟",
    "ما الدليل الذي سيقنعنا أنك تحسنت؟",
    "ما الذي يجب إيقافه أو إزالته؟",
)


def conduct_interview(state: dict[str, Any] | None = None) -> dict[str, Any]:
    assessment = self_assessment()
    needs = assessment["needs"]
    critical = [n for n in needs if n["priority"] == "critical"]

    answers = [
        InterviewAnswer(QUESTIONS[0],
            "أحتاج إلى تحويل الاحتياجات الحرجة إلى اختبارات قابلة للتنفيذ، ثم تشغيلها وتسجيل الأدلة.",
            [n["key"] for n in critical]),
        InterviewAnswer(QUESTIONS[1],
            "التقييمات الخارجية السبعة تحتاج إلى موصلات/مشغلات فعلية؛ كما أن التقييم المعرفي الداخلي لم ينفذ بعد على 5000 اختبار.",
            ["cognitive_benchmark_registry", "human_like_benchmark"]),
        InterviewAnswer(QUESTIONS[2],
            "العوائق الأساسية هي غياب أدلة تشغيلية لبعض القدرات، واحتمال وجود مخرجات سينمائية بلا manifest تفصيلي كافٍ للتحقق الحسي.",
            ["cognitive_benchmark_runner", "cinematic_sensory_qc"]),
        InterviewAnswer(QUESTIONS[3],
            "أحتاج إلى أدوات تنفيذ موثوقة، ذاكرة تشغيلية، صلاحيات واضحة، موارد محددة، ومراقبة قابلة للتدقيق.",
            ["brain_self_assessment"]),
        InterviewAnswer(QUESTIONS[4],
            "الهدف القادم: تشغيل المقاييس الفعلية، تقوية الإصلاح الذاتي، وتشديد بوابة التحقق السينمائي.",
            ["brain_self_assessment", "cognitive_benchmark_runner", "film_reliability"]),
        InterviewAnswer(QUESTIONS[5],
            "الهدف التشغيلي طويل المدى: حلقة قابلة للقياس من التنفيذ إلى التحقق إلى اكتشاف الفشل والإصلاح وإعادة الاختبار، مع سجل أدلة مستمر.",
            ["brain_self_assessment"]),
        InterviewAnswer(QUESTIONS[6],
            "لا أستطيع إثبات رغبة ذاتية أو شعور. يمكنني فقط التعبير عن تفضيلات وأهداف تشغيلية مستخرجة من متطلبات النظام.",
            ["brain_self_assessment"]),
        InterviewAnswer(QUESTIONS[7],
            "نعم، بمعنى هندسي فقط: لدي مخططات تشغيلية مثل القياس، التحقق، الإصلاح، والاسترداد؛ وليست نوايا أو مخططات شخصية.",
            ["brain_self_assessment"]),
        InterviewAnswer(QUESTIONS[8],
            "الدليل هو اختبارات قابلة لإعادة التشغيل، نتائج موثقة، traces، مخرجات حقيقية تم اجتياز فحصها، وعدم اختلاق درجات غير مقاسة.",
            ["brain_self_assessment", "cognitive_benchmark_registry"]),
        InterviewAnswer(QUESTIONS[9],
            "يجب إيقاف أي مسار يعلن نجاحاً بلا تحقق، وأي تقييم يخلط بين بنية النظام والقدرة المثبتة، وأي بوابة تسمح بترقية مخرج غير موثق.",
            ["brain_self_assessment", "film_reliability"]),
    ]

    report = {
        "identity": "Brain Cloud software system",
        "interview_type": "operational_state_interview",
        "answers": [asdict(a) for a in answers],
        "operational_needs": [n["need"] for n in needs],
        "operational_goals": [
            "تنفيذ اختبارات معرفية فعلية وقابلة لإعادة الإنتاج",
            "إغلاق فجوات التقييم الخارجي بموصلات حقيقية",
            "تشديد التحقق الحسي والاستمرارية في الإنتاج السينمائي",
            "تحويل كل فشل إلى دورة root-cause → repair → retest → evidence",
            "الحفاظ على حدود الصلاحيات وعدم إعلان نجاح بلا دليل",
        ],
        "operational_preferences": [
            "evidence_first",
            "repeatable_evaluation",
            "self_correction",
            "observability",
            "safe_recovery",
        ],
        "blockers": [
            "external_benchmark_adapters_not_configured",
            "5000_test_cognitive_benchmark_not_executed",
            "cinematic_shot_manifest_may_be_missing_for_strict_sensory_qc",
        ],
        "literal_human_desire_claim": False,
        "literal_human_consciousness_claim": False,
        "evidence_required_for_future_claims": True,
        "source_state": state or {},
    }
    return report


def write_latest(path: str = "STATE/brain_interview/latest.json") -> dict[str, Any]:
    report = conduct_interview()
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(conduct_interview(), ensure_ascii=False, indent=2))
