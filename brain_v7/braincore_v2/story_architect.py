"""Story Architect: converts an idea into an executable screenplay state graph."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from hashlib import sha256
from typing import Any
import re

@dataclass(frozen=True)
class Beat:
    beat_id:str; act:int; purpose:str; event:str; conflict:str; character_change:str
    setup_refs:tuple[str,...]; payoff_refs:tuple[str,...]; visual_motif:str; audio_motif:str

@dataclass(frozen=True)
class StoryPlan:
    story_id:str; premise:str; theme:str; logline:str; acts:tuple[dict[str,Any],...]
    beats:tuple[Beat,...]; open_threads:tuple[str,...]; motifs:tuple[str,...]
    state_rules:tuple[str,...]

def _id(x:str)->str: return sha256(x.encode()).hexdigest()[:12]

def build_story(objective:str, genre:str="cinematic")->StoryPlan:
    objective=objective.strip()
    if not objective: raise ValueError("objective must not be empty")
    sid="story-"+_id(objective+"|"+genre)
    acts=(
      {"act":1,"name":"SETUP","function":"establish world, protagonist, desire and question"},
      {"act":2,"name":"ESCALATION","function":"raise obstacles, reveal information and force choices"},
      {"act":3,"name":"TRANSFORMATION","function":"decisive action changes character and situation"},
      {"act":4,"name":"PAYOFF","function":"resolve major threads and leave a resonant final image"},
    )
    purposes=("hook","inciting incident","first choice","complication","reversal","revelation",
              "escalation","moral choice","climax","consequence","resolution","final image")
    beats=[]
    for i,p in enumerate(purposes,1):
        act=1 if i<=3 else 2 if i<=7 else 3 if i<=10 else 4
        beats.append(Beat(
          f"{sid}-B{i:02d}",act,p,
          f"Advance the story through {p}; never repeat information already established.",
          "A concrete obstacle or uncertainty must oppose the protagonist's current objective.",
          "The protagonist's knowledge, decision, relationship or situation must change.",
          () if i==1 else (f"{sid}-B{i-1:02d}",),
          (f"{sid}-B{i+1:02d}",) if i<12 else (),
          "recurring visual motif that evolves with the protagonist",
          "recurring sonic motif that changes with emotional state"))
    return StoryPlan(sid,objective,
      "Theme emerges through choices and consequences rather than exposition.",
      f"A character pursues a concrete goal while escalating consequences force a meaningful choice: {objective}.",
      acts,tuple(beats),(f"{sid}-main-question",),("light","threshold","hero prop","silence"),
      ("track character state","track location/time","track props","track wounds/changes","track relationships","track unresolved threads"))

def export_story(plan:StoryPlan)->dict[str,Any]:
    return asdict(plan)
