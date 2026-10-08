from brain_v12.youtube.content_integrity import (
    ContentFingerprint,
    ExperimentRecord,
    duplicate_content,
    unique_experiments,
)
from brain_v12.youtube.measurement import VideoMeasurement
from brain_v12.youtube.measurement_gate import validate_measurement


def fp(video_id, script="s1", asset="a1"):
    return ContentFingerprint(video_id, "ai", "story", script, asset)


def test_content_duplicate_is_detected():
    assert duplicate_content(fp("v2"), [fp("v1")])


def test_changed_script_is_not_duplicate():
    assert not duplicate_content(fp("v2", script="s2"), [fp("v1")])


def test_experiments_are_deduplicated():
    records = [
        ExperimentRecord("e1", "v1", "hook", "A"),
        ExperimentRecord("e1", "v1", "hook", "A"),
        ExperimentRecord("e2", "v2", "hook", "B"),
    ]
    assert [r.experiment_id for r in unique_experiments(records)] == ["e1", "e2"]


def test_measurement_gate_rejects_small_sample():
    m = VideoMeasurement("v1", 50, 5, 100, 1, "2026-10-08T04:00:00Z")
    result = validate_measurement(m)
    assert result.usable is False
    assert result.reason == "INSUFFICIENT_IMPRESSIONS"


def test_measurement_gate_accepts_sufficient_sample():
    m = VideoMeasurement("v1", 1000, 100, 2000, 5, "2026-10-08T04:00:00Z")
    result = validate_measurement(m)
    assert result.usable is True
    assert result.confidence == 1.0
