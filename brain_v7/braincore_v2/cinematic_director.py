"""Cinematic Director: multi-shot film grammar with backend-aware shot routing."""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
from typing import Any
from .cinematic_bible import build_bibles
from .genre_engine import creative_contract


@dataclass(frozen=True)
class Shot:
    shot_id: str; scene_id: str; duration_s: float; purpose: str; action: str; framing: str; lens: str
    camera_move: str; composition: str; lighting: str; color_grade: str; continuity_key: str
    visual_prompt: str; audio_prompt: str; transition: str; negative_prompt: str
    image_reference_prompt: str; sound_design_prompt: str; voice_prompt: str


@dataclass(frozen=True)
class Scene:
    scene_id: str; title: str; purpose: str; setting: str; characters: tuple[str, ...]; props: tuple[str, ...]
    lighting: str; color_grade: str; shots: tuple[Shot, ...]


@dataclass(frozen=True)
class CinematicPlan:
    plan_id: str; objective: str; commercial_goal: str; audience: str; hook: str; scenes: tuple[Scene, ...]
    continuity_ledger: dict[str, Any]; character_bible: dict[str, Any]; world_bible: dict[str, Any]
    quality_targets: dict[str, float]; monetization_routes: tuple[str, ...]; creative_contract: dict[str, Any] | None = None


def _id(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()[:12]


def _route_for_shot(role: str) -> dict[str, Any]:
    if role == "ESTABLISH":
        return {"generation_mode": "t2v_or_i2v", "reference_policy": "world_anchor", "continuity_policy": "world_first"}
    if role == "PERFORMANCE":
        return {"generation_mode": "i2v", "reference_policy": "character_anchor+last_frame", "continuity_policy": "identity_first"}
    return {"generation_mode": "i2v", "reference_policy": "prop_anchor+previous_frame", "continuity_policy": "match_cut"}


def _shot(scene, n, duration, purpose, action, framing, lens, move, composition, lighting, grade,
          continuity, objective, transition, character_dna, world_dna):
    sid = f"{scene}-S{n:02d}"
    role = ("ESTABLISH", "PERFORMANCE", "INSERT")[n - 1]
    route = _route_for_shot(role)
    visual = (
        f"Cinematic master shot {sid}. {action}. Objective: {objective}. {framing}, {lens}, {move}, {composition}. "
        f"{lighting}, {grade}. CHARACTER DNA: {character_dna}. WORLD DNA: {world_dna}. Continuity key: {continuity}. "
        f"Photorealistic feature-film cinematography, natural anatomy, stable facial identity, stable wardrobe, "
        f"coherent geometry, realistic skin texture, real lens depth-of-field, motivated shadows, cinematic exposure, "
        f"temporal consistency, no visual drift."
    )
    audio = f"Arabic cinematic soundscape for {sid}: natural ambience, synchronized Foley, clean dialogue/narration, room tone, recurring music motif."
    negative = "cartoon, plastic skin, wax face, deformed hands, extra fingers, duplicate person, identity drift, warped geometry, broken perspective, flicker, jitter, temporal morphing, watermark, logo"
    image_ref = f"MASTER REFERENCE for {sid}: preserve face, hair, age, proportions, wardrobe, hero prop and world geometry. Strategy: {route['reference_policy']}."
    sound = "Foley and ambience follow action; preserve acoustic environment and music motif; dialogue remains intelligible."
    voice = "Arabic natural human cinematic narration/dialogue; stable speaker identity, accent, emotion and microphone character."
    return Shot(sid, scene, duration, purpose, action, framing, lens, move, composition, lighting, grade,
                continuity, visual, audio, transition, negative, image_ref, sound, voice)


def build_plan(objective: str, *, commercial_goal="YouTube revenue",
               audience="Arabic-speaking general audience", duration_s=60) -> CinematicPlan:
    objective = objective.strip()
    if not objective:
        raise ValueError("objective must not be empty")
    duration_s = max(30, min(600, int(duration_s)))
    b = build_bibles(objective, audience=audience)
    contract = creative_contract(objective, audience)
    c, w = b["character_bible"], b["world_bible"]
    grammar = [
        ("SC01", "HOOK", "Immediate attention", "wide establishing", "35mm", "slow push-in", "rule of thirds", "Reveal the world and central visual mystery.", "extreme wide", "fade-in"),
        ("SC02", "PROBLEM", "Create tension and relevance", "medium", "50mm", "subtle handheld", "subject isolation", "Show the protagonist encountering the central problem.", "over-shoulder", "match-cut"),
        ("SC03", "SOLUTION", "Deliver transformation", "tracking medium", "50mm", "controlled dolly", "leading lines", "Show the decisive action that changes the situation.", "close-up", "match-cut"),
        ("SC04", "PAYOFF", "Resolve and motivate next action", "hero close-up", "85mm", "slow pull-back", "center-weighted hero", "Reveal consequence and emotional payoff.", "wide hero", "clean end card"),
    ]
    continuity = f"film-{_id(objective)}"
    d = duration_s / 12
    scenes = []
    for sid, title, purpose, framing, lens, move, comp, action, insert_frame, transition in grammar:
        shots = []
        for j in range(1, 4):
            f = framing if j == 1 else (insert_frame if sid in ("SC02", "SC04") else "medium close-up")
            a = f"{action} {'Establish geography and spatial relationships.' if j == 1 else 'Focus on protagonist performance.' if j == 2 else 'Emphasize the story-relevant detail.'}"
            shots.append(_shot(sid, j, d, purpose, a, f, lens, move, comp,
                               "motivated cinematic key + soft fill + practicals",
                               "consistent cinematic grade; protected skin tones", continuity, objective,
                               transition if j == 3 else "motivated cut", c["face_identity"] + "; " + c["wardrobe"],
                               w["geography"] + "; " + w["time_of_day"] + "; " + w["palette"]))
        scenes.append(Scene(sid, title, purpose, "same coherent cinematic world", ("Primary Subject",),
                            ("hero prop", "persistent environment"), "motivated cinematic key + soft fill + practicals",
                            "consistent cinematic grade", tuple(shots)))
    quality = {"prompt_alignment": .94, "visual_quality": .94, "audio_quality": .92, "cinematic_coherence": .96,
               "character_consistency": .95, "world_consistency": .95, "motion_realism": .93,
               "lighting_realism": .93, "dialogue_clarity": .92, "technical_validity": .98}
    return CinematicPlan(f"cin-{_id(objective + str(duration_s))}", objective, commercial_goal, audience,
        "Open with an immediate visual question, conflict or striking result; establish curiosity before explanation.",
        tuple(scenes), {"characters": c, "world": w, "shot_grammar": "12-shot: establish -> perform -> insert across four acts",
        "creative_contract": contract, "genre": contract["genre"], "factuality": contract["factuality"],
        "camera": "35/50/85mm progression with motivated movement", "lighting": "preserve direction, exposure and practical sources",
        "audio": "stable voice identity, ambience and recurring music motif"}, c, w, quality,
        ("youtube_ads_when_channel_is_eligible", "sponsorship_or_brand_deal", "affiliate_or_product_link",
         "lead_generation_for_paid_service"), contract)


def provider_prompts(plan: CinematicPlan) -> list[dict[str, Any]]:
    result = []
    for scene in plan.scenes:
        for s in scene.shots:
            role = ("ESTABLISH", "PERFORMANCE", "INSERT")[int(s.shot_id[-2:]) - 1]
            result.append({
                "shot_id": s.shot_id, "scene_id": s.scene_id, "visual_prompt": s.visual_prompt,
                "audio_prompt": s.audio_prompt, "continuity_key": s.continuity_key, "duration_s": s.duration_s,
                "purpose": s.purpose, "framing": s.framing, "lens": s.lens, "camera_move": s.camera_move,
                "transition": s.transition, "character_bible": plan.character_bible, "world_bible": plan.world_bible,
                "negative_prompt": s.negative_prompt, "image_reference_prompt": s.image_reference_prompt,
                "sound_design_prompt": s.sound_design_prompt, "voice_prompt": s.voice_prompt,
                "generation": _route_for_shot(role), "quality_targets": plan.quality_targets,
                "creative_contract": plan.creative_contract,
                "production_rules": {"photorealism": True, "identity_consistency": True, "world_consistency": True,
                                    "temporal_consistency": True, "audio_sync": True, "no_text_artifacts": True},
            })
    return result


def refine_plan(plan: CinematicPlan, feedback: dict[str, float]) -> dict[str, Any]:
    weak = [k for k, v in feedback.items() if float(v) < .82]
    return {"status": "REFINE_REQUIRED" if weak else "ACCEPTED", "weak_criteria": weak,
            "next_pass": ["tighten hook", "strengthen character/world locks", "synchronize narration and music",
                          "improve payoff", "reroute failed shot to alternate backend"] if weak else [], "plan_id": plan.plan_id}


def snapshot() -> dict[str, Any]:
    return {"cinematic_director": True, "shot_planning": True, "multi_shot_scene_graph": True,
            "character_bible": True, "world_bible": True, "continuity_ledger": True, "camera_language": True,
            "audio_direction": True, "provider_neutral": True, "backend_aware_routing": True,
            "guaranteed_revenue": False, "external_publication": "permission_gated"}
