from __future__ import annotations

import json

from brain_v12.brain.error_logs import BrainErrorLogStore


def test_records_and_reads_error_event(tmp_path):
    store = BrainErrorLogStore(tmp_path / "errors.jsonl")
    event = store.record(
        category="test_failure",
        message="deliberate test error",
        component="unit-test",
        source="tests/test_error_logs.py:12",
        context={"run_id": "run-123"},
    )
    assert event["event_id"]
    assert event["trace_id"]
    assert event["repair"]["status"] == "PENDING"
    assert store.get(event["event_id"])["message"] == "deliberate test error"
    assert store.list(category="test_failure")[0]["component"] == "unit-test"


def test_redacts_secret_fields_and_bearer_tokens(tmp_path):
    store = BrainErrorLogStore(tmp_path / "errors.jsonl")
    event = store.record(
        category="security_test",
        message="Authorization: Bearer abc.def.secret",
        context={"api_key": "dont-store-me", "safe": "visible"},
    )
    serialized = json.dumps(event)
    assert "dont-store-me" not in serialized
    assert "abc.def.secret" not in serialized
    assert event["context"]["api_key"] == "[REDACTED]"
    assert event["context"]["safe"] == "visible"


def test_filters_by_severity_and_ignores_corrupt_lines(tmp_path):
    path = tmp_path / "errors.jsonl"
    store = BrainErrorLogStore(path)
    store.record(category="one", message="warning", severity="WARNING")
    store.record(category="two", message="error", severity="ERROR")
    with path.open("a", encoding="utf-8") as stream:
        stream.write("{invalid json}\n")
    events = store.list(severity="ERROR")
    assert len(events) == 1
    assert events[0]["category"] == "two"
