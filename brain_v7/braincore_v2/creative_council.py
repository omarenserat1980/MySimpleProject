"""Electronic Brain Creative Council: writer, director, cinematographer, sound designer and factual/reverence critics."""
from __future__ import annotations
from typing import Any
from .genre_engine import creative_contract

ROLES=("showrunner_writer","screenwriter","director","cinematographer","production_designer",
       "editor","sound_designer","composer","continuity_supervisor","fact_checker","ethics_reverence_reviewer")

def build_council(objective:str, audience:str="Arabic-speaking general audience")->dict[str,Any]:
    contract=creative_contract(objective,audience)
    return {
      "objective":objective,
      "roles":list(ROLES),
      "contract":contract,
      "workflow":[
        "WRITER: premise -> theme -> characters -> beats -> scenes -> dialogue",
        "DIRECTOR: beats -> blocking -> shot grammar -> performance -> transitions",
        "CINEMATOGRAPHER: lens -> framing -> lighting -> exposure -> movement -> color",
        "PRODUCTION_DESIGNER: world -> architecture -> props -> wardrobe -> continuity",
        "SOUND: dialogue -> ambience -> Foley -> music motif -> dynamics -> mix",
        "EDITOR: rhythm -> coverage -> match cuts -> emotional timing -> final structure",
        "CRITICS: factuality/reverence + continuity + visual quality + audio quality",
        "REPAIR: convert each detected defect into a targeted regeneration instruction"
      ],
      "handoff_contract":"Every role reads the same FilmDSL contract; no role may silently change identity, world, chronology or factual claims."
    }
