"""FilmDSL: structured creative contract shared by writer, director, generation and QC agents."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any
import json

@dataclass(frozen=True)
class FilmSpec:
    genre: str
    subgenre: str
    tone: str
    era: str
    setting: str
    audience: str
    language: str
    realism: str
    factuality: str
    religious_sensitivity: str
    visual_style: str
    narrative_engine: str
    sound_style: str
    camera_language: str
    continuity_rules: tuple[str, ...]
    research_requirements: tuple[str, ...]
    prohibited_shortcuts: tuple[str, ...]

def infer_genre(objective: str) -> str:
    text=objective.lower()
    if any(x in text for x in ("علمي","science","scientific","فضاء","space","طب","medical")): return "scientific"
    if any(x in text for x in ("ديني","religious","إسلام","islam","قرآن","prophet","نبي")): return "religious"
    if any(x in text for x in ("وثائقي","documentary","تاريخ","history")): return "documentary"
    if any(x in text for x in ("رعب","horror","thriller","رعب")): return "thriller"
    if any(x in text for x in ("كوميدي","comedy")): return "comedy"
    if any(x in text for x in ("خيال علمي","sci-fi","science fiction")): return "science_fiction"
    return "cinematic"

PROFILES: dict[str, dict[str, Any]] = {
 "cinematic":{"tone":"dramatic","realism":"photorealistic","factuality":"creative",
  "visual_style":"feature-film naturalism","narrative_engine":"character desire -> obstacle -> choice -> consequence",
  "sound_style":"motivated production sound + score","camera_language":"motivated lens and blocking"},
 "scientific":{"tone":"curious, rigorous","realism":"photorealistic","factuality":"evidence-first",
  "visual_style":"cinematic scientific visualization","narrative_engine":"question -> evidence -> experiment -> implication",
  "sound_style":"clean narration + restrained score + precise Foley","camera_language":"clear explanatory compositions"},
 "science_fiction":{"tone":"wonder with grounded stakes","realism":"photorealistic","factuality":"internally_consistent",
  "visual_style":"physically plausible speculative cinema","narrative_engine":"discovery -> escalation -> sacrifice -> consequence",
  "sound_style":"original atmospheric score + physical sound","camera_language":"scale contrast + motivated movement"},
 "documentary":{"tone":"observational","realism":"photorealistic","factuality":"source-verified",
  "visual_style":"observational realism","narrative_engine":"question -> testimony/evidence -> context -> conclusion",
  "sound_style":"location sound first","camera_language":"observational with restrained intervention"},
 "religious":{"tone":"reverent, humane","realism":"photorealistic","factuality":"source-verified where factual",
  "visual_style":"respectful historical/reflective cinema","narrative_engine":"context -> moral question -> reflection -> consequence",
  "sound_style":"natural ambience + respectful original score","camera_language":"calm, purposeful, non-sensational"},
 "thriller":{"tone":"tense","realism":"photorealistic","factuality":"creative","visual_style":"grounded suspense cinema",
  "narrative_engine":"threat -> uncertainty -> reveal -> irreversible choice","sound_style":"dynamic tension + precise Foley",
  "camera_language":"motivated instability only when narratively justified"},
 "comedy":{"tone":"light, character-driven","realism":"photorealistic","factuality":"creative","visual_style":"naturalistic comedy",
  "narrative_engine":"desire -> misunderstanding -> escalation -> payoff","sound_style":"clean dialogue + rhythmic Foley",
  "camera_language":"clarity-first coverage"},
}

def build_film_spec(objective:str, *, audience:str, language:str="Arabic") -> FilmSpec:
    genre=infer_genre(objective)
    p=PROFILES.get(genre,PROFILES["cinematic"])
    religious = "strictly respectful; distinguish scripture/tradition from dramatization" if genre=="religious" else "not_applicable"
    research = ("verify factual claims against authoritative sources before generation",
                "keep a source ledger for factual assertions") if p["factuality"] in ("evidence-first","source-verified") else ()
    return FilmSpec(genre,genre,p["tone"],"as specified by story","as specified by story",audience,language,p["realism"],
                    p["factuality"],religious,p["visual_style"],p["narrative_engine"],p["sound_style"],
                    p["camera_language"],("identity_lock","world_lock","time_lock","prop_lock","audio_motif_lock"),
                    research,("generic filler","unmotivated camera movement","continuity-breaking redesign","fabricated factual claim"))

def to_dict(spec:FilmSpec)->dict[str,Any]:
    return asdict(spec)

def to_json(spec:FilmSpec)->str:
    return json.dumps(to_dict(spec),ensure_ascii=False,indent=2)
