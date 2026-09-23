"""Quality-driven multimedia orchestration.

The brain does not claim that one generator is universally best. It evaluates
available providers against the current creative brief, keeps multiple
candidates when useful, scores outputs against explicit criteria, and can
request a refinement pass before accepting a result.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Mapping


@dataclass(frozen=True)
class QualityCriterion:
    name: str
    weight: float


DEFAULT_CRITERIA = (
    QualityCriterion("prompt_alignment", 0.25),
    QualityCriterion("visual_quality", 0.20),
    QualityCriterion("audio_quality", 0.15),
    QualityCriterion("cinematic_coherence", 0.20),
    QualityCriterion("brand_fit", 0.10),
    QualityCriterion("technical_validity", 0.10),
)


@dataclass(frozen=True)
class ProviderProfile:
    name: str
    capabilities: tuple[str, ...]
    reliability: float = 0.5
    latency: float = 0.5
    quality: float = 0.5


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def provider_score(profile: ProviderProfile, *, kind: str) -> float:
    capability = 1.0 if kind in profile.capabilities else 0.0
    return _clamp(
        capability * (
            0.50 * profile.quality
            + 0.25 * profile.reliability
            + 0.15 * (1.0 - profile.latency)
            + 0.10
        )
    )


def rank_providers(
    profiles: list[ProviderProfile],
    *,
    kind: str,
) -> list[dict[str, Any]]:
    ranked = [
        {
            "provider": p.name,
            "score": provider_score(p, kind=kind),
            "capability_match": kind in p.capabilities,
        }
        for p in profiles
        if kind in p.capabilities
    ]
    return sorted(ranked, key=lambda x: x["score"], reverse=True)


def quality_score(
    scores: Mapping[str, float],
    criteria: tuple[QualityCriterion, ...] = DEFAULT_CRITERIA,
) -> float:
    total_weight = sum(c.weight for c in criteria)
    if total_weight <= 0:
        return 0.0
    return sum(
        _clamp(scores.get(c.name, 0.0)) * c.weight
        for c in criteria
    ) / total_weight


def acceptance_gate(
    scores: Mapping[str, float],
    *,
    minimum: float = 0.82,
) -> dict[str, Any]:
    score = quality_score(scores)
    return {
        "score": score,
        "minimum": minimum,
        "accepted": score >= minimum,
        "action": "ACCEPT" if score >= minimum else "REFINE",
    }


def build_creative_brief(
    objective: str,
    *,
    cinematic: bool = True,
    language: str = "ar",
) -> dict[str, Any]:
    return {
        "objective": objective.strip(),
        "language": language,
        "cinematic": cinematic,
        "continuity": {
            "characters": True,
            "setting": True,
            "lighting": True,
            "color_logic": True,
            "camera_language": True,
        },
        "audio": {
            "voice_consistency": True,
            "mix_balance": True,
            "music_sync": True,
            "effects_sync": True,
        },
        "quality_gate": asdict(acceptance_gate({})),
        "criteria": [asdict(c) for c in DEFAULT_CRITERIA],
    }


def orchestration_snapshot() -> dict[str, Any]:
    return {
        "provider_agnostic": True,
        "multi_provider_selection": True,
        "candidate_evaluation": True,
        "refinement_loop": True,
        "cinematic_continuity": True,
        "universal_best_claim": False,
    }
