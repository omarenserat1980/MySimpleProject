"""Deterministic, free-first electronic game factory catalog and build planner."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from enum import Enum
from hashlib import sha256

class GameGenre(str, Enum):
    PUZZLE="PUZZLE"; ARCADE="ARCADE"; STRATEGY="STRATEGY"; EDUCATIONAL="EDUCATIONAL"; STORY="STORY"

@dataclass(frozen=True)
class GameSpec:
    game_id: str
    title: str
    genre: GameGenre
    platform: str
    price_jod: float
    status: str = "PLANNED"
    @property
    def fingerprint(self) -> str:
        raw="|".join((self.game_id,self.title,self.genre.value,self.platform,str(self.price_jod)))
        return sha256(raw.encode("utf-8")).hexdigest()[:16]

class GameFactory:
    def create(self,title:str,genre:GameGenre=GameGenre.ARCADE,platform:str="WEB",price_jod:float=2.0)->GameSpec:
        if not title.strip(): raise ValueError("title is required")
        if price_jod < 0: raise ValueError("price_jod must be non-negative")
        game_id="GAME-"+sha256(title.strip().encode("utf-8")).hexdigest()[:12]
        return GameSpec(game_id,title.strip(),genre,platform,price_jod)
    def manifest(self,games:list[GameSpec])->list[dict]:
        return [asdict(g)|{"genre":g.genre.value,"fingerprint":g.fingerprint} for g in games]
