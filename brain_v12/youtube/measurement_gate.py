"""Measurement evidence quality and anti-self-deception gates."""

from __future__ import annotations

from dataclasses import dataclass

from .measurement import VideoMeasurement


@dataclass(frozen=True)
class MeasurementGate:
    usable: bool
    confidence: float
    reason: str


def validate_measurement(
    measurement: VideoMeasurement,
    *,
    minimum_impressions: int = 100,
    minimum_views: int = 10,
) -> MeasurementGate:
    if measurement.impressions < minimum_impressions:
        return MeasurementGate(False, 0.0, "INSUFFICIENT_IMPRESSIONS")
    if measurement.views < minimum_views:
        return MeasurementGate(False, 0.0, "INSUFFICIENT_VIEWS")

    coverage = min(measurement.impressions / 1000, 1.0)
    view_signal = min(measurement.views / 100, 1.0)
    confidence = (coverage * 0.5) + (view_signal * 0.5)
    return MeasurementGate(True, confidence, "MEASUREMENT_USABLE")
