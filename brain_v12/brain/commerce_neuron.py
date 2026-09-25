from __future__ import annotations

from typing import Any


COMMERCE_PHASES = [
    {"id": "website", "title": "إكمال الموقع", "executor": "website_executor", "side_effect": True},
    {"id": "products", "title": "إنشاء وتجهيز المنتجات الرقمية", "executor": "product_executor", "side_effect": True},
    {"id": "catalog", "title": "تحديث الكتالوج وتجربة الشراء", "executor": "catalog_executor", "side_effect": True},
    {"id": "marketing", "title": "التسويق والنشر", "executor": "marketing_executor", "side_effect": True},
    {"id": "payment", "title": "ربط الدفع الإلكتروني", "executor": "payment_executor", "side_effect": True},
]


def build_commerce_plan(goal: str) -> dict[str, Any]:
    """Return an ordered plan; payment is deliberately last."""
    return {
        "goal": goal,
        "mode": "AUTONOMOUS_ORCHESTRATION",
        "phases": [dict(p, status="PENDING") for p in COMMERCE_PHASES],
        "rules": {
            "payment_last": True,
            "verify_before_delivery": True,
            "no_claim_without_evidence": True,
        },
    }


def next_phase(plan: dict[str, Any]) -> dict[str, Any] | None:
    for phase in plan.get("phases", []):
        if phase.get("status") == "PENDING":
            return phase
    return None
