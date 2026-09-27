"""Unified persistent production memory facade."""
from __future__ import annotations
from pathlib import Path
from .film_memory import FilmMemory
from .world_state import WorldState

class ProductionMemory:
    def __init__(self,root="."):
        root=Path(root); self.film=FilmMemory((root/"film_memory.json").as_posix()); self.world=WorldState((root/"world_state.json").as_posix())
    def context(self,entity_ids=None):
        return {"film":self.film.snapshot(),"world":self.world.context(entity_ids)}
    def commit_evidence(self,shot_id, evidence, entities=None):
        self.film.update_shot(shot_id,evidence)
        for e in entities or []:
            self.world.upsert(e["entity_id"],e.get("kind","entity"),e.get("attributes",{}),{"shot_id":shot_id,"evidence":e.get("evidence",{})})
        return self.context()
