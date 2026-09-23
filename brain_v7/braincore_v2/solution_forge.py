"""Creative Solution Forge: generate, critique, and refine multiple solution ideas.

This module is deliberately bounded and evidence-aware. It can invent candidate
solutions, score them, and request another ideation round when the frontier is
too weak. It never grants permissions or performs irreversible side effects.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class SolutionIdea:
    idea_id: str
    title: str
    concept: str
    novelty: float
    usefulness: float
    feasibility: float
    earning_leverage: float
    evidence: float
    risk: float
    effort: float
    score: float
    next_test: str


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _score(novelty: float, usefulness: float, feasibility: float,
           earning: float, evidence: float, risk: float, effort: float) -> float:
    # Reward novelty/usefulness/economics/evidence; penalize risk and effort.
    return round(
        100 * (
            0.18 * novelty
            + 0.24 * usefulness
            + 0.18 * feasibility
            + 0.20 * earning
            + 0.12 * evidence
            + 0.05 * (1.0 - risk)
            + 0.03 * (1.0 - effort)
        ),
        2,
    )


def _make(idea_id: str, title: str, concept: str, novelty: float,
          usefulness: float, feasibility: float, earning: float,
          evidence: float, risk: float, effort: float,
          next_test: str) -> SolutionIdea:
    values = [novelty, usefulness, feasibility, earning, evidence, risk, effort]
    novelty, usefulness, feasibility, earning, evidence, risk, effort = map(_clamp, values)
    return SolutionIdea(
        idea_id, title, concept, novelty, usefulness, feasibility, earning,
        evidence, risk, effort,
        _score(novelty, usefulness, feasibility, earning, evidence, risk, effort),
        next_test,
    )


def generate_ideas(problem: str, round_no: int = 1) -> list[SolutionIdea]:
    """Generate diverse candidates instead of one premature solution."""
    p = str(problem).strip() or "increase verified earning capability"
    r = max(1, int(round_no))

    base = [
        _make("forge-1", "محرك تحويل الفرص إلى منتجات جاهزة",
               f"حوّل المشكلة ({p}) إلى حزمة قابلة للبيع: اكتشاف → تحقق → إنتاج → تسليم → إثبات نتيجة.",
               .72, .92, .82, .91, .72, .18, .45,
               "اختبر على فرصة واحدة حقيقية وسجّل الزمن والنتيجة."),
        _make("forge-2", "مولّد عروض متعدد المسارات",
               f"أنشئ عدة طرق لحل ({p}) ثم ولّد عرضاً مختلفاً لكل نوع عميل بدلاً من عرض واحد للجميع.",
               .86, .84, .76, .88, .62, .20, .50,
               "اختبر ثلاث صيغ عرض على ثلاث فرص موثقة دون إرسال تلقائي."),
        _make("forge-3", "حلقة التجربة الأسرع",
               f"ابنِ تجربة صغيرة منخفضة التكلفة لـ({p})، قِس النتيجة، ثم عدّل الفكرة قبل الاستثمار الأكبر.",
               .79, .86, .88, .80, .78, .12, .32,
               "نفّذ تجربة قابلة للعكس وحدد مقياس نجاح قبل التنفيذ."),
        _make("forge-4", "تركيب قدرات غير متجاورة",
               f"ادمج قدرات البحث + الفيديو + الكتابة + تحليل الربحية لصنع حل جديد للمشكلة ({p}).",
               .94, .89, .61, .93, .55, .28, .63,
               "أنشئ نموذجاً أولياً صغيراً وأثبت كل مكوّن منفرداً."),
        _make("forge-5", "مضاعف الدخل من أصل واحد",
               f"حوّل مخرجاً واحداً من ({p}) إلى عدة مخرجات مشروعة: نص، فيديو، صورة، وصف، وحزمة نشر.",
               .83, .91, .74, .95, .68, .16, .48,
               "احسب تكلفة إعادة الاستخدام وسجّل الإيراد الفعلي فقط بعد الدفع."),
    ]
    if r > 1:
        # Second and later rounds deliberately shift toward combinations,
        # constraints, and anti-obvious approaches.
        extras = [
            _make(f"forge-r{r}-a", "حل قائم على إزالة الاختناق",
                   f"بدلاً من تحسين ({p}) مباشرة، حدّد أكبر اختناق في السلسلة وأزل هذا الاختناق أولاً.",
                   .90, .90, .79, .89, .66, .15, .42,
                   "قِس زمن كل مرحلة وحدد المرحلة الأعلى كلفة."),
            _make(f"forge-r{r}-b", "شبكة حلول قابلة لإعادة الاستخدام",
                   f"حوّل مكونات ({p}) إلى قوالب وموصلات قابلة لإعادة الاستخدام عبر فرص متعددة.",
                   .88, .87, .83, .92, .70, .13, .46,
                   "اختبر إعادة استخدام مكوّن واحد في فرصتين مختلفتين."),
        ]
        base.extend(extras)
    return base


def evaluate_ideas(ideas: Iterable[SolutionIdea]) -> list[dict[str, Any]]:
    return [asdict(x) for x in sorted(ideas, key=lambda x: x.score, reverse=True)]


def review_frontier(ideas: Iterable[SolutionIdea], minimum_score: float = 72.0) -> dict[str, Any]:
    ranked = evaluate_ideas(ideas)
    if not ranked:
        return {"status": "REQUEST_MORE_IDEAS", "reason": "NO_CANDIDATES", "ideas": []}
    best = ranked[0]
    if best["score"] < float(minimum_score):
        return {
            "status": "REQUEST_MORE_IDEAS",
            "reason": "FRONTIER_TOO_WEAK",
            "minimum_score": minimum_score,
            "best_score": best["score"],
            "ideas": ranked,
        }
    return {
        "status": "READY_FOR_SELECTION",
        "best_candidate": best,
        "ideas": ranked,
        "selection_rule": "highest scored candidate; verify evidence and test before irreversible action",
    }


def forge(problem: str, rounds: int = 2, minimum_score: float = 72.0) -> dict[str, Any]:
    """Run bounded ideation rounds and return the strongest evidence-aware frontier."""
    rounds = max(1, min(int(rounds), 4))
    all_ideas: list[SolutionIdea] = []
    history: list[dict[str, Any]] = []
    for r in range(1, rounds + 1):
        batch = generate_ideas(problem, r)
        all_ideas.extend(batch)
        review = review_frontier(all_ideas, minimum_score)
        history.append({"round": r, "review": review})
        if review["status"] == "READY_FOR_SELECTION":
            return {
                "status": "READY_FOR_SELECTION",
                "rounds_used": r,
                "problem": problem,
                "selected": review["best_candidate"],
                "ideas": review["ideas"],
                "history": history,
                "requires_execution_approval": True,
            }
    final = review_frontier(all_ideas, minimum_score)
    return {
        "status": final["status"],
        "rounds_used": rounds,
        "problem": problem,
        "selected": final.get("best_candidate"),
        "ideas": final["ideas"],
        "history": history,
        "requires_execution_approval": True,
    }
