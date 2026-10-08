"""Unified YouTube production gate for the single Brain orchestrator.

Combines channel viability, video ranking, and video economics without side effects.
"""

from __future__ import annotations

from dataclasses import dataclass

from .channel_strategy import ChannelDecision, ChannelProfile, evaluate_channel
from .revenue_factory import ContentDecision, VideoCandidate, rank_video
from .video_economics import VideoEconomicAction, VideoEconomicDecision, VideoEconomics, decide_video_economics


@dataclass(frozen=True)
class ProductionGateResult:
    channel: ChannelDecision
    content: ContentDecision
    economics: VideoEconomicDecision
    allowed: bool
    reason: str


def evaluate_production_gate(
    channel: ChannelProfile,
    candidate: VideoCandidate,
    economics: VideoEconomics,
) -> ProductionGateResult:
    if candidate.video_id != economics.video_id:
        raise ValueError("candidate and economics video IDs must match")

    channel_result = evaluate_channel(channel)
    content_result = rank_video(candidate)
    economics_result = decide_video_economics(economics)

    if not channel_result.viable:
        return ProductionGateResult(channel_result, content_result, economics_result, False, "CHANNEL_NOT_VIABLE")
    if not content_result.selected:
        return ProductionGateResult(channel_result, content_result, economics_result, False, "VIDEO_NOT_SELECTED")
    if economics_result.action is VideoEconomicAction.KILL:
        return ProductionGateResult(channel_result, content_result, economics_result, False, "VIDEO_ECONOMICS_KILL")

    return ProductionGateResult(channel_result, content_result, economics_result, True, "PRODUCTION_ALLOWED")
