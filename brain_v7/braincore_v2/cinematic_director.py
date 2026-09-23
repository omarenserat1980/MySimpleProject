"""Cinematic Director: turns a commercial objective into a production-ready shot plan.

Provider-neutral and permission-gated. It plans scenes, shots, continuity, sound,
thumbnail/title hooks and refinement criteria; it does not claim guaranteed
audience or revenue and does not publish externally by itself.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
from typing import Any


@dataclass(frozen=True)
class Shot:
    shot_id: str
    scene_id: str
    duration_s: float
    purpose: str
    action: str
    framing: str
    lens: str
    camera_move: str
    composition: str
    lighting: str
    color_grade: str
    continuity_key: str
    visual_prompt: str
    audio_prompt: str
    transition: str


@dataclass(frozen=True)
class Scene:
    scene_id: str
    title: str
    purpose: str
    setting: str
    characters: tuple[str, ...]
    props: tuple[str, ...]
    lighting: str
    color_grade: str
    shots: tuple[Shot, ...]


@dataclass(frozen=True)
class CinematicPlan:
    plan_id: str
    objective: str
    commercial_goal: str
    audience: str
    hook: str
    scenes: tuple[Scene, ...]
    continuity_ledger: dict[str, Any]
    quality_targets: dict[str, float]
    monetization_routes: tuple[str, ...]


def _id(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()[:12]


def _shot(scene: str, n: int, duration: float, purpose: str, action: str,
          framing: str, lens: str, move: str, composition: str,
          lighting: str, grade: str, continuity: str, objective: str,
          transition: str) -> Shot:
    sid = f"{scene}-S{n:02d}"
    return Shot(
        shot_id=sid, scene_id=scene, duration_s=duration, purpose=purpose,
        action=action, framing=framing, lens=lens, camera_move=move,
        composition=composition, lighting=lighting, color_grade=grade,
        continuity_key=continuity,
        visual_prompt=(
            f"Cinematic shot {sid}. {action}. Objective: {objective}. "
            f"{framing}, {lens}, {move}, {composition}, {lighting}, {grade}. "
            f"Maintain continuity key {continuity}."
        ),
        audio_prompt=(
            f"Arabic cinematic sound for {sid}: narration aligned to action, "
            f"controlled ambience, music transition, clean dialogue."
        ),
        transition=transition,
    )


def build_plan(objective: str, *, commercial_goal: str = "YouTube revenue",
               audience: str = "Arabic-speaking general audience",
               duration_s: int = 60) -> CinematicPlan:
    objective = objective.strip()
    if not objective:
        raise ValueError("objective must not be empty")
    duration_s = max(30, min(600, int(duration_s)))
    hook = (
        "Open with a visually immediate problem, promise or surprising result; "
        "delay the explanation until curiosity is established."
    )
    # A bounded 4-act structure scales with target duration.
    d = duration_s / 4.0
    scenes = []
    specs = [
        ("SC01", "HOOK", "Immediate attention", "cinematic environment",
         "wide establishing shot", "35mm", "slow push-in", "rule of thirds"),
        ("SC02", "PROBLEM", "Create tension and relevance", "same world",
         "medium shot", "50mm", "subtle handheld", "subject isolation"),
        ("SC03", "SOLUTION", "Deliver the useful transformation", "same world",
         "tracking medium", "50mm", "controlled dolly", "leading lines"),
        ("SC04", "PAYOFF", "Resolve and create a next action", "same world",
         "hero close-up", "85mm", "slow pull-back", "center-weighted hero"),
    ]
    for i, (sid, title, purpose, setting, framing, lens, move, comp) in enumerate(specs, 1):
        continuity = f"world-{_id(objective + setting)}"
        lighting = "motivated cinematic key + soft fill + practicals"
        grade = "consistent cinematic grade; protect skin tones and brand accents"
        shot = _shot(
            sid, 1, d, purpose,
            f"Advance the {title.lower()} beat for: {objective}",
            framing, lens, move, comp, lighting, grade, continuity, objective,
            "match-cut" if i < 4 else "clean end card",
        )
        scenes.append(Scene(
            scene_id=sid, title=title, purpose=purpose, setting=setting,
            characters=("primary subject",), props=("story-relevant prop",),
            lighting=lighting, color_grade=grade, shots=(shot,),
        ))

    ledger = {
        "characters": {"primary subject": "appearance, wardrobe and voice remain stable"},
        "world": "same geography, time-of-day logic and visual language",
        "props": "important props persist unless explicitly removed",
        "camera": "35/50/85mm progression; motivated movement only",
        "lighting": "direction and intensity remain coherent across cuts",
        "audio": "voice identity, ambience and music motif remain consistent",
    }
    quality = {
        "prompt_alignment": 0.90,
        "visual_quality": 0.90,
        "audio_quality": 0.88,
        "cinematic_coherence": 0.92,
        "brand_fit": 0.88,
        "technical_validity": 0.95,
    }
    return CinematicPlan(
        plan_id=f"cin-{_id(objective + str(duration_s))}",
        objective=objective,
        commercial_goal=commercial_goal,
        audience=audience,
        hook=hook,
        scenes=tuple(scenes),
        continuity_ledger=ledger,
        quality_targets=quality,
        monetization_routes=(
            "youtube_ads_when_channel_is_eligible",
            "sponsorship_or_brand_deal",
            "affiliate_or_product_link",
            "lead_generation_for_paid_service",
        ),
    )


def provider_prompts(plan: CinematicPlan) -> list[dict[str, Any]]:
    return [
        {
            "shot_id": shot.shot_id,
            "scene_id": shot.scene_id,
            "visual_prompt": shot.visual_prompt,
            "audio_prompt": shot.audio_prompt,
            "continuity_key": shot.continuity_key,
            "duration_s": shot.duration_s,
        }
        for scene in plan.scenes for shot in scene.shots
    ]


def refine_plan(plan: CinematicPlan, feedback: dict[str, float]) -> dict[str, Any]:
    weak = [k for k, v in feedback.items() if float(v) < 0.82]
    return {
        "status": "REFINE_REQUIRED" if weak else "ACCEPTED",
        "weak_criteria": weak,
        "next_pass": [
            "tighten hook in first 3 seconds",
            "increase visual specificity",
            "strengthen continuity prompts",
            "synchronize narration and music",
            "improve payoff and call-to-action",
        ] if weak else [],
        "plan_id": plan.plan_id,
    }


def snapshot() -> dict[str, Any]:
    return {
        "cinematic_director": True,
        "shot_planning": True,
        "continuity_ledger": True,
        "camera_language": True,
        "audio_direction": True,
        "commercial_goal": True,
        "provider_neutral": True,
        "guaranteed_revenue": False,
        "external_publication": "permission_gated",
    }
