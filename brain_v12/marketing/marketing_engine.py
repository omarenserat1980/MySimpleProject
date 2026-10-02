"""Electronic Brain Marketing Engine.

Governed campaign lifecycle:
DRAFT -> REVIEW -> APPROVED -> SCHEDULED -> PUBLISHED -> MEASURED
with REJECTED/CANCELLED terminal states.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


class CampaignState(str, Enum):
    DRAFT = "DRAFT"
    REVIEW = "REVIEW"
    APPROVED = "APPROVED"
    SCHEDULED = "SCHEDULED"
    PUBLISHED = "PUBLISHED"
    MEASURED = "MEASURED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


_ALLOWED = {
    CampaignState.DRAFT: {CampaignState.REVIEW, CampaignState.CANCELLED},
    CampaignState.REVIEW: {CampaignState.APPROVED, CampaignState.REJECTED},
    CampaignState.APPROVED: {CampaignState.SCHEDULED, CampaignState.CANCELLED},
    CampaignState.SCHEDULED: {CampaignState.PUBLISHED, CampaignState.CANCELLED},
    CampaignState.PUBLISHED: {CampaignState.MEASURED},
    CampaignState.MEASURED: set(),
    CampaignState.REJECTED: set(),
    CampaignState.CANCELLED: set(),
}


@dataclass
class Campaign:
    name: str
    objective: str
    audience: str
    channels: list[str]
    content: str = ""
    id: str = field(default_factory=lambda: str(uuid4()))
    state: CampaignState = CampaignState.DRAFT
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    approvals: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)

    def transition(self, target: CampaignState, actor: str, reason: str = "") -> None:
        if target not in _ALLOWED[self.state]:
            raise ValueError(f"Invalid campaign transition: {self.state} -> {target}")
        event = {
            "at": datetime.now(timezone.utc).isoformat(),
            "from": self.state.value,
            "to": target.value,
            "actor": actor,
            "reason": reason,
        }
        self.events.append(event)
        self.state = target

    def approve(self, actor: str, note: str = "") -> None:
        self.approvals.append(
            {
                "at": datetime.now(timezone.utc).isoformat(),
                "actor": actor,
                "note": note,
            }
        )
        self.transition(CampaignState.APPROVED, actor, note)

    def record_metrics(self, actor: str, **metrics: float) -> None:
        if self.state != CampaignState.PUBLISHED:
            raise ValueError("Metrics can be recorded after publication only")
        self.metrics.update(metrics)
        self.transition(CampaignState.MEASURED, actor, "Outcome metrics recorded")


class MarketingEngine:
    """In-memory reference engine; persistence belongs to the Brain data layer."""

    def __init__(self) -> None:
        self.campaigns: dict[str, Campaign] = {}

    def create_campaign(
        self,
        name: str,
        objective: str,
        audience: str,
        channels: list[str],
        content: str = "",
    ) -> Campaign:
        campaign = Campaign(name, objective, audience, channels, content)
        self.campaigns[campaign.id] = campaign
        return campaign

    def get(self, campaign_id: str) -> Campaign:
        return self.campaigns[campaign_id]
