"""Character and world continuity bibles for the cinematic factory."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from hashlib import sha256
from typing import Any

def _id(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()[:12]

@dataclass(frozen=True)
class CharacterBible:
    character_id: str
    name: str
    role: str
    appearance: str
    wardrobe: str
    hair: str
    face_identity: str
    body_language: str
    voice_identity: str
    continuity_rules: tuple[str, ...]

@dataclass(frozen=True)
class WorldBible:
    world_id: str
    name: str
    geography: str
    era: str
    architecture: str
    weather: str
    time_of_day: str
    palette: str
    props: tuple[str, ...]
    continuity_rules: tuple[str, ...]

def build_bibles(objective: str, *, audience: str) -> dict[str, Any]:
    key=_id(objective)
    character=CharacterBible(
        character_id=f"char-{key}", name="Primary Subject", role="protagonist",
        appearance="consistent adult subject; natural proportions; realistic skin and facial detail",
        wardrobe="single coherent wardrobe across the film unless a scene explicitly changes it",
        hair="stable haircut, hairline, length and texture",
        face_identity="identity lock: same facial geometry, eyes, nose, jawline and age across every shot",
        body_language="natural restrained cinematic performance",
        voice_identity="stable Arabic voice identity, pace and emotional register",
        continuity_rules=("no identity drift","no wardrobe drift","no age drift","no unexplained accessories"),
    )
    world=WorldBible(
        world_id=f"world-{key}", name="Primary Cinematic World",
        geography="one coherent physical location with consistent spatial relationships",
        era="contemporary unless the story explicitly requires another period",
        architecture="photorealistic architecture consistent with the location",
        weather="stable weather continuity unless motivated by story",
        time_of_day="consistent sun direction and ambient exposure between connected shots",
        palette="cinematic neutral palette with controlled accent color and protected skin tones",
        props=("story-relevant hero prop","persistent environmental details"),
        continuity_rules=("preserve geography","preserve lighting direction","preserve weather","preserve hero props"),
    )
    return {"character_bible":asdict(character),"world_bible":asdict(world),"audience":audience}
