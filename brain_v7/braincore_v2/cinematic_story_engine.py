"""Lightweight story engine for the cinematic factory.

Creates a deterministic 4-act Arabic-friendly story brief without a large model.
It is a planning layer: no claims of originality or guaranteed audience response.
"""
from __future__ import annotations

from hashlib import sha256
from typing import Any


def _id(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()[:12]


def build_story(objective: str, *, audience: str = "Arabic-speaking YouTube audience") -> dict[str, Any]:
    objective = objective.strip()
    if not objective:
        raise ValueError("objective must not be empty")
    seed = _id(objective)
    return {
        "story_id": f"story-{seed}",
        "objective": objective,
        "audience": audience,
        "logline": f"رحلة سينمائية حول: {objective}",
        "acts": [
            {"act": "HOOK", "seconds": 8, "beat": "سؤال أو خطر بصري يفتح فضول المشاهد"},
            {"act": "PROBLEM", "seconds": 16, "beat": "تصعيد المشكلة وإظهار ما هو على المحك"},
            {"act": "SOLUTION", "seconds": 20, "beat": "اكتشاف أو تحول بصري يقود للحل"},
            {"act": "PAYOFF", "seconds": 16, "beat": "نتيجة واضحة ونهاية تترك فكرة أو سؤالًا"},
        ],
        "visual_identity": {
            "camera": "35mm establishing, 50mm tension, 85mm payoff",
            "lighting": "motivated key, soft fill, practical highlights",
            "grade": "deep contrast, controlled highlights, consistent skin/object tones",
            "motion": "slow push, motivated tracking, restrained pull-back",
        },
        "continuity_key": f"world-{seed}",
        "next_test": "render all acts and inspect continuity before publication",
    }
