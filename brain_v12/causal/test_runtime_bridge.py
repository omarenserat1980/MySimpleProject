"""Tests for truthful causal-runtime evidence reporting."""
from brain_v12.causal.runtime_bridge import build_report


def test_empty_event_stream_is_not_reported_as_recorded_evidence():
    report = build_report([], source="test-events.jsonl")

    assert report["status"] == "NO_RUNTIME_EVIDENCE"
    assert report["event_count"] == 0
    assert report["record_count"] == 0
    assert report["records"] == []


def test_runtime_events_with_observed_outcome_create_evidence_record():
    events = [
        {"job_id": "job-1", "event": "attempt_started"},
        {
            "job_id": "job-1",
            "event": "checkpoint",
            "data": {"step_index": 1},
        },
    ]

    report = build_report(events, source="test-events.jsonl")

    assert report["status"] == "RECORDED"
    assert report["event_count"] == 2
    assert report["record_count"] == 1
    assert report["records"][0]["cause"] == "attempt_started"
    assert report["records"][0]["effect"] == "checkpoint"
    assert report["records"][0]["observed"] == 1
    assert report["records"][0]["successes"] == 1
