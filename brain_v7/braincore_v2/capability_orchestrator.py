"""Automatic capability selection and bounded production planning."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class CapabilityPlan:
    objective: str
    primary: str
    capabilities: tuple[str, ...]
    stages: tuple[str, ...]
    external_actions_required: bool = False


KEYWORDS = {
    "image": ("صورة", "صور", "image", "photo", "creative"),
    "video": ("فيديو", "فيديوهات", "video", "reel", "short"),
    "audio": ("صوت", "تعليق صوتي", "voice", "audio", "tts"),
    "web": ("موقع", "ويب", "website", "web", "متجر"),
    "app": ("تطبيق", "app", "android", "mobile", "ios"),
    "software": ("برنامج", "برمج", "كود", "software", "automation", "api"),
    "design": ("تصميم", "design", "ui", "ux"),
}


def select_capabilities(objective: str) -> list[str]:
    text = objective.lower()
    found = [
        capability
        for capability, words in KEYWORDS.items()
        if any(word in text for word in words)
    ]
    if not found:
        found = ["software"]
    return list(dict.fromkeys(found))


def build_plan(objective: str) -> CapabilityPlan:
    capabilities = select_capabilities(objective)
    primary = capabilities[0]
    stages = (
        "UNDERSTAND",
        "PLAN",
        "CREATE_LOCAL_ARTIFACTS",
        "INTEGRATE_CAPABILITIES",
        "VERIFY_OUTPUT",
        "LEARN_AND_REPLAN",
    )
    return CapabilityPlan(objective, primary, tuple(capabilities), stages)


def execution_plan(objective: str) -> dict[str, Any]:
    plan = build_plan(objective)
    return {
        "status": "READY_FOR_LOCAL_EXECUTION",
        "plan": asdict(plan),
        "pipeline": [
            {"stage": stage, "capabilities": list(plan.capabilities)}
            for stage in plan.stages
        ],
        "external_submission": False,
        "payment_execution": False,
        "requires_authorization_for_external_actions": True,
    }


def snapshot() -> dict[str, Any]:
    return {
        "automatic_selection": True,
        "local_pipeline": True,
        "supported": sorted(
            {"software", "web", "app", "image", "audio", "video", "design"}
        ),
        "external_actions": "permission_gated",
    }
