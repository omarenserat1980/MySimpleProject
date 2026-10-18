"""Tests for truthful causal-runtime evidence reporting."""
from pathlib import Path

from brain_v12.causal import runtime_bridge
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


def test_runtime_home_path_matches_brain_supervisor_layout(monkeypatch, tmp_path):
    runtime_home = tmp_path / "persistent-brain"
    monkeypatch.setenv("BRAIN_RUNTIME_HOME", str(runtime_home))

    expected = (
        runtime_home
        / "brain6_artifacts"
        / "supervisor"
        / "control_plane"
        / "events.jsonl"
    )
    assert runtime_bridge.resolve_events_path() == expected


def test_legacy_repo_stream_is_used_when_runtime_stream_is_missing(
    monkeypatch, tmp_path
):
    monkeypatch.delenv("BRAIN_RUNTIME_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setattr(runtime_bridge, "ROOT", tmp_path / "repo")

    legacy = tmp_path / "repo" / "brain6_artifacts" / "control_plane" / "events.jsonl"
    legacy.parent.mkdir(parents=True)
    legacy.write_text('{"job_id":"job-legacy","event":"attempt_started"}\n', encoding="utf-8")

    assert runtime_bridge.resolve_events_path() == legacy
    assert runtime_bridge.read_events(legacy)[0]["job_id"] == "job-legacy"
