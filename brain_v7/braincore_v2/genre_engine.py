"""Genre intelligence layer: converts a FilmSpec into writer/director/QC rules."""
from __future__ import annotations
from typing import Any
from .film_dsl import build_film_spec, to_dict

def creative_contract(objective:str, audience:str="Arabic-speaking general audience")->dict[str,Any]:
    spec=build_film_spec(objective,audience=audience)
    d=to_dict(spec)
    d["writer_rules"]=[
        "Every scene must change information, emotion, stakes or character state.",
        "Plant callbacks before payoffs; avoid exposition when action can communicate it.",
        "Track cause -> effect across scenes and preserve unresolved threads until payoff."
    ]
    d["director_rules"]=[
        "Every camera movement must have narrative motivation.",
        "Use visual contrast, blocking, light and sound to communicate subtext.",
        "Prefer coverage that remains editable while preserving a deliberate visual point of view."
    ]
    d["qc_rules"]=[
        "Reject identity drift, world drift, temporal flicker and physics-breaking motion.",
        "Reject dialogue/audio mismatch and inconsistent acoustic perspective.",
        "For factual genres, reject unsupported claims; for religious stories, flag dramatization clearly in metadata."
    ]
    return d
