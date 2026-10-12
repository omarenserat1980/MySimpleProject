"""Single decision facade for the YouTube content lifecycle."""

from __future__ import annotations

from dataclasses import dataclass

from .channel_strategy import ChannelProfile
from .measurement import VideoMeasurement
from .production_gate import ProductionGateResult, evaluate_production_gate
from .qc_gate import PublishDecision, QcReport, evaluate_publish_gate
from .revenue_factory import VideoCandidate
from .video_economics import VideoEconomics


@dataclass(frozen=True)
class LifecycleDecision:
    production: ProductionGateResult
    publish_decision: PublishDecision
    measurement_quality: str
    next_action: str


def evaluate_lifecycle(
    channel: ChannelProfile,
    candidate: VideoCandidate,
    economics: VideoEconomics,
    qc: QcReport,
    measurement: VideoMeasurement | None = None,
) -> LifecycleDecision:
    production = evaluate_production_gate(channel, candidate, economics)

    if not production.allowed:
        return LifecycleDecision(
            production,
            PublishDecision.BLOCK,
            "NOT_MEASURED",
            "DO_NOT_PRODUCE",
        )

    publish = evaluate_publish_gate(qc)
    if publish is not PublishDecision.READY:
        return LifecycleDecision(
            production,
            publish,
            "NOT_MEASURED",
            "FIX_QC",
        )

    if measurement is None:
        return LifecycleDecision(
            production,
            publish,
            "NOT_MEASURED",
            "PUBLISH_THEN_MEASURE",
        )

    if measurement.video_id != candidate.video_id:
        raise ValueError("measurement video ID must match candidate video ID")

    from .measurement import measurement_quality
    quality = measurement_quality(measurement)
    return LifecycleDecision(
        production,
        publish,
        quality,
        "LEARN_FROM_RESULTS" if quality == "MEASURABLE" else "COLLECT_MORE_DATA",
    )
