"""Bridge between the opportunity engine and continuous development.

Turns the highest-priority eligible opportunity into a development objective
and then feeds the next cycle back into opportunity selection. This is an
internal planning/execution bridge; external submission and payment remain
permission-gated.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Iterable

from .opportunity_autopilot import OpportunityPlan, rank, plan_from_lead
from .continuous_self_developer import next_development_cycle


def choose_opportunity(leads: Iterable[dict[str, Any]]) -> dict[str, Any] | None:
    plans = [plan_from_lead(x) for x in leads]
    if not plans:
        return None
    return rank(plans)[0]


def development_objective(
    iteration: int,
    leads: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    opportunity = choose_opportunity(leads)
    cycle = next_development_cycle(max(1, iteration))

    if opportunity is None:
        return {
            "status": "DEVELOPMENT_ONLY",
            "cycle": asdict(cycle),
            "opportunity": None,
            "feedback": "لا توجد فرصة حالية؛ استمر في تحسين القدرة التالية.",
        }

    service = opportunity["service"] or "general"
    objective = (
        f"طوّر قدرة {cycle.domain} لخدمة الفرصة الأعلى أولوية: "
        f"{opportunity['title']} ({service}). "
        "أنشئ أو حسّن الأصل المحلي المطلوب ثم أعد ترتيب الفرص."
    )
    return {
        "status": "OPPORTUNITY_DRIVEN_DEVELOPMENT",
        "cycle": {**asdict(cycle), "objective": objective},
        "opportunity": opportunity,
        "feedback": "نتيجة الفرصة الحالية تحدد اتجاه الدورة التالية.",
        "external_submission": False,
        "payment_execution": False,
    }


def next_cycle(iteration: int, leads: Iterable[dict[str, Any]]) -> dict[str, Any]:
    return development_objective(max(1, iteration), leads)
