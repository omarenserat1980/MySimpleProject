"""Post-publish measurement primitives. Analytics only, never revenue."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VideoMeasurement:
    video_id: str
    impressions: int
    views: int
    watch_time_seconds: float
    subscribers_gained: int
    measured_at: str

    def __post_init__(self) -> None:
        if not self.video_id or not self.measured_at:
            raise ValueError("video identity and measurement time are required")
        if min(self.impressions, self.views, self.watch_time_seconds, self.subscribers_gained) < 0:
            raise ValueError("measurement values cannot be negative")

    @property
    def view_rate(self) -> float:
        return self.views / self.impressions if self.impressions else 0.0

    @property
    def average_watch_seconds(self) -> float:
        return self.watch_time_seconds / self.views if self.views else 0.0

    @property
    def subscriber_rate(self) -> float:
        return self.subscribers_gained / self.views if self.views else 0.0


def measurement_quality(measurement: VideoMeasurement) -> str:
    if measurement.impressions == 0 and measurement.views == 0:
        return "INSUFFICIENT_DATA"
    if measurement.views == 0:
        return "LOW_SIGNAL"
    return "MEASURABLE"
