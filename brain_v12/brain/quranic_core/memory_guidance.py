"""Read-only Quran-informed review guidance for Brain memory.

This module translates references in cloud.quran_heart_corpus into engineering
review prompts. It does not store memories, interpret verses as software facts,
or claim spiritual attributes for the system.
"""
from __future__ import annotations

from cloud.quran_heart_corpus import HEART_CORPUS

# Deliberately conservative, explicit keyword mapping. A match is a prompt for
# review, not proof that a memory is true or false.
REVIEW_TERMS = {
    "evidence_and_verification": (
        "evidence", "verify", "verification", "proof", "source", "دليل",
        "تحقق", "مصدر", "إثبات", "برهان",
    ),
    "uncertainty_and_doubt": (
        "uncertain", "uncertainty", "doubt", "unknown", "maybe", "شك",
        "غير مؤكد", "احتمال", "مجهول",
    ),
    "correction_and_learning": (
        "error", "wrong", "correct", "correction", "learn", "lesson",
        "خطأ", "تصحيح", "تعلم", "درس",
    ),
    "attention_and_goal_drift": (
        "goal", "objective", "drift", "attention", "priority", "هدف",
        "انحراف", "انتباه", "أولوية",
    ),
    "conflict_and_reconciliation": (
        "conflict", "dispute", "reconcile", "coordination", "خلاف",
        "نزاع", "تعارض", "تنسيق", "مصالحه",
    ),
    "privacy_and_accountability": (
        "private", "sensitive", "secret", "accountability", "audit",
        "خصوصية", "حساس", "سر", "مساءلة", "تدقيق",
    ),
    "humility_and_counterevidence": (
        "certain", "certainty", "assumption", "counterevidence", "challenge",
        "يقين", "افتراض", "دليل مضاد", "اعتراض",
    ),
}

THEME_GROUPS = {
    "evidence_and_verification": {"tranquility through evidence", "perception and fabrication", "active listening and witness state"},
    "uncertainty_and_doubt": {"doubt", "fear/doubt", "stress-induced pessimistic hypotheses"},
    "correction_and_learning": {"correction and return after error", "testing/refinement", "declining sensitivity to evidence and correction"},
    "attention_and_goal_drift": {"heedless heart", "attention drift from the governing objective"},
    "conflict_and_reconciliation": {"reconciliation", "reconciliation of hearts"},
    "privacy_and_accountability": {"hidden information", "accountability of hearts", "concealing testimony"},
    "humility_and_counterevidence": {"pride/hardening", "humility/softening", "deviation/ambiguity", "following desires"},
}


def principles() -> list[dict]:
    """Return source-linked guidance without reproducing or altering Quran text."""
    return [
        {
            "reference": item.ref,
            "theme": item.theme,
            "engineering_principle": item.engineering_principle,
        }
        for item in HEART_CORPUS
    ]


def review_memory(memory_text: str) -> dict:
    """Suggest review lenses; never mutate or score the truth of a memory."""
    text = str(memory_text or "").casefold().strip()
    if not text:
        return {
            "ok": False,
            "status": "EMPTY_MEMORY",
            "matches": [],
            "message": "أدخل نص الذاكرة المطلوب مراجعته.",
        }

    matched_groups = [
        group for group, terms in REVIEW_TERMS.items()
        if any(term.casefold() in text for term in terms)
    ]
    matches = [
        item for item in HEART_CORPUS
        if any(item.theme in THEME_GROUPS[group] for group in matched_groups)
    ]
    return {
        "ok": True,
        "status": "REVIEW_SUGGESTIONS_ONLY" if matches else "NO_EXPLICIT_KEYWORD_MATCH",
        "matched_review_lenses": matched_groups,
        "matches": [
            {
                "reference": item.ref,
                "theme": item.theme,
                "engineering_principle": item.engineering_principle,
            }
            for item in matches
        ],
        "limitations": [
            "النتائج اقتراحات مراجعة بالكلمات المفتاحية وليست تفسيرًا شرعيًا.",
            "لا تُعدّل الذاكرة ولا تثبت صحة المعلومة أو بطلانها.",
            "يجب التحقق من نص الآية والسياق والتفسير من مصدر موثوق قبل الاستشهاد.",
        ],
    }
