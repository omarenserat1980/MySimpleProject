"""Read-only HTTP boundary for the YouTube Control Plane."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .channel_strategy import ChannelProfile
from .content_integrity import ContentFingerprint
from .control_plane import control_video
from .execution_plan import compile_execution_plan
from .qc_gate import QcReport
from .revenue_factory import VideoCandidate
from .video_economics import VideoEconomics

router = APIRouter(prefix="/api/youtube/control", tags=["youtube-control"])


class ControlInput(BaseModel):
    channel_id: str
    language: str
    niche: str
    audience_fit: float = Field(ge=0, le=1)
    demand: float = Field(ge=0, le=1)
    competition: float = Field(ge=0, le=1)
    production_fit: float = Field(ge=0, le=1)
    monetization_fit: float = Field(ge=0, le=1)
    originality_headroom: float = Field(ge=0, le=1)

    video_id: str
    title_angle: str
    expected_demand: float = Field(ge=0, le=1)
    production_cost: float = Field(ge=0, le=1)
    production_risk: float = Field(ge=0, le=1)
    originality: float = Field(ge=0, le=1)

    production_hours: float = Field(ge=0)
    tool_cost_usd: float = Field(ge=0)
    asset_cost_usd: float = Field(ge=0)
    expected_views: int = Field(ge=0)
    expected_rpm_usd: float = Field(ge=0)
    success_probability: float = Field(ge=0, le=1)
    learning_value: float = Field(default=0, ge=0, le=1)

    technical_pass: bool
    cinematic_pass: bool
    duration_seconds: float = Field(ge=0)
    has_audio: bool
    has_video: bool
    originality_confirmed: bool
    policy_risk: float = Field(default=0, ge=0, le=1)

    script_fingerprint: str
    asset_fingerprint: str
    existing_fingerprints: list[dict] = Field(default_factory=list)


@router.post("/evaluate")
def evaluate_youtube_control(item: ControlInput):
    try:
        channel = ChannelProfile(
            item.channel_id, item.language, item.niche,
            item.audience_fit, item.demand, item.competition,
            item.production_fit, item.monetization_fit, item.originality_headroom,
        )
        candidate = VideoCandidate(
            item.video_id, item.niche, item.title_angle,
            item.expected_demand, item.production_cost,
            item.production_risk, item.originality,
        )
        economics = VideoEconomics(
            item.video_id, item.production_hours, item.tool_cost_usd,
            item.asset_cost_usd, item.expected_views, item.expected_rpm_usd,
            item.success_probability, item.learning_value,
        )
        qc = QcReport(
            item.technical_pass, item.cinematic_pass, item.duration_seconds,
            item.has_audio, item.has_video, item.originality_confirmed,
            item.policy_risk,
        )
        fingerprint = ContentFingerprint(
            item.video_id, item.niche, item.title_angle,
            item.script_fingerprint, item.asset_fingerprint,
        )
        existing = [
            ContentFingerprint(
                str(x["video_id"]), str(x["niche"]), str(x["title_angle"]),
                str(x["script_fingerprint"]), str(x["asset_fingerprint"]),
            )
            for x in item.existing_fingerprints
        ]
        decision = control_video(
            channel, candidate, economics, qc, fingerprint, existing,
        )
        plan = compile_execution_plan(decision)
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return {
        "video_id": item.video_id,
        "action": decision.action,
        "duplicate": decision.duplicate,
        "production_allowed": decision.lifecycle.production.allowed,
        "publish_decision": decision.lifecycle.publish_decision.value,
        "next_action": decision.lifecycle.next_action,
        "execution_plan": [step.value for step in plan.steps],
        "requires_publish_authorization": plan.requires_publish_authorization,
        "side_effects": plan.side_effects,
        "audit": {
            "decision_id": decision.audit.decision_id,
            "reason": decision.audit.reason,
            "fingerprint": decision.audit.fingerprint(),
        },
    }
