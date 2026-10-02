"""Durable media learning records without autonomous external publishing."""
from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class MediaMemory:
    campaigns: list[dict] = field(default_factory=list)

    def record(self, campaign: dict) -> None:
        self.campaigns.append(campaign)

    def latest(self, limit: int = 10) -> list[dict]:
        return self.campaigns[-max(0, limit):]
