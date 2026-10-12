"""Top-level YouTube control decision.

This is a pure facade: it records what should happen, not what happened.
"""

from __future__ import annotations

from dataclasses import dataclass

from .channel_strategy import ChannelProfile
from .content_integrity import ContentFingerprint, duplicate_content
from .decision_ledger import DecisionRecord
from .lifecycle import LifecycleDecision, evaluate_lifecycle
from .measurement import VideoMeasurement
from .production_gate import ProductionGateResult
from .qc_gate import QcReport
from .revenue_factory import VideoCandidate
from .video_economics import VideoEconomics


@dataclass(frozen=True)
class ControlDecision:
    lifecycle: LifecycleDecision
    duplicate: bool
    action: str
    audit: DecisionRecord


def control_video(
    channel: ChannelProfile,
    candidate: VideoCandidate,
    economics: VideoEconomics,
    qc: QcReport,
    fingerprint: ContentFingerprint,
    existing_fingerprints: list[ContentFingerprint],
    measurement: VideoMeasurement | None = None,
) -> ControlDecision:
    if fingerprint.video_id != candidate.video_id:
        raise ValueError("fingerprint video ID must match candidate video ID")

    duplicate = duplicate_content(fingerprint, existing_fingerprints)
    lifecycle = evaluate_lifecycle(channel, candidate, economics, qc, measurement)

    if duplicate:
        action = "BLOCK_DUPLICATE"
    else:
        action = lifecycle.next_action

    audit = DecisionRecord(
        decision_id=f"youtube:{candidate.video_id}:{lifecycle.next_action}",
        video_id=candidate.video_id,
        stage="YOUTUBE_CONTROL",
        action=action,
        reason="DUPLICATE_CONTENT" if duplicate else lifecycle.next_action,
        evidence_refs=(fingerprint.digest,),
    )
    return ControlDecision(lifecycle, duplicate, action, audit)
