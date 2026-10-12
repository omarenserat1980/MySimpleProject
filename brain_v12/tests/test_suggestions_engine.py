from __future__ import annotations

import json

import pytest

from brain_v12.brain.error_logs import BrainErrorLogStore
from brain_v12.brain.suggestions_engine import BrainSuggestionsEngine


class FakeProvider:
    def __init__(self, result=None):
        self.result = result or {"ok": True, "provider": "openai", "model": "test-model", "reply": json.dumps({
            "component": "api",
            "problem_summary": "API request failed",
            "supporting_evidence": ["traceback observed"],
            "probable_root_cause": "Dependency timeout (hypothesis)",
            "proposed_solution": "Add bounded timeout handling",
            "alternative_solutions": ["Improve retry policy"],
            "affected_files": ["brain_v12/example.py"],
            "severity": "HIGH",
            "confidence": 0.7,
            "priority": "HIGH",
            "risk_assessment": "Low risk if tested",
            "required_permissions": ["human approval"],
            "implementation_plan": ["Add regression test", "Implement bounded timeout"],
            "test_plan": ["Run targeted tests"],
            "rollback_plan": ["Revert patch if tests fail"]
        })}

    def respond(self, **kwargs):
        return self.result


def _engine(tmp_path, provider=None):
    logs = BrainErrorLogStore(tmp_path / "errors.jsonl")
    logs.record(category="test_error", message="request timed out", component="api",
                source="brain_v12/example.py:10", severity="ERROR",
                context={"request_id": "req-1"})
    return BrainSuggestionsEngine(provider or FakeProvider(), logs, tmp_path / "suggestions.db"), logs


def test_analyze_persists_structured_suggestion(tmp_path):
    engine, _ = _engine(tmp_path)
    result = engine.analyze(limit=10)
    item = result["results"][0]["suggestion"]
    assert item["status"] == "READY_FOR_REVIEW"
    assert item["provider"] == "openai"
    assert item["payload"]["incident_id"]
    assert item["payload"]["verification_result"]["status"] == "NOT_VERIFIED"
    assert engine._get(item["suggestion_id"])["suggestion_id"] == item["suggestion_id"]


def test_duplicate_event_is_not_recommended_twice(tmp_path):
    engine, _ = _engine(tmp_path)
    first = engine.analyze()
    second = engine.analyze()
    assert first["results"][0]["duplicate"] is False
    assert second["results"][0]["duplicate"] is True


def test_provider_failure_creates_explicit_local_fallback(tmp_path):
    engine, _ = _engine(tmp_path, FakeProvider({"ok": False, "error": "OPENAI_NETWORK_ERROR"}))
    item = engine.analyze()["results"][0]["suggestion"]
    assert item["status"] == "NEW"
    assert item["provider"] == "none"
    assert item["payload"]["provider_fallback"] is True
    assert item["payload"]["probable_root_cause"].startswith("NOT_DETERMINED")


def test_rejection_requires_reason_and_verification_evidence(tmp_path):
    engine, _ = _engine(tmp_path)
    item = engine.analyze()["results"][0]["suggestion"]
    with pytest.raises(ValueError, match="REJECTION_REASON_REQUIRED"):
        engine.transition(item["suggestion_id"], "reject")
    approved = engine.transition(item["suggestion_id"], "approve", reason="Reviewed")
    assert approved["status"] == "APPROVED"
    with pytest.raises(ValueError, match="VERIFICATION_REQUIRES_PASS_AND_EVIDENCE"):
        engine.transition(item["suggestion_id"], "verify", outcome={"passed": True, "evidence": []})
    verified = engine.transition(item["suggestion_id"], "verify",
                                 outcome={"passed": True, "evidence": ["pytest exit code 0"]})
    assert verified["status"] == "VERIFIED"
    assert verified["payload"]["verification_result"]["status"] == "VERIFIED"



def test_provider_exception_is_captured_as_local_fallback(tmp_path):
    class RaisingProvider:
        def respond(self, **kwargs):
            raise TimeoutError("provider timeout")

    engine, _ = _engine(tmp_path, RaisingProvider())
    item = engine.analyze()["results"][0]["suggestion"]
    assert item["provider"] == "none"
    assert item["status"] == "NEW"
    assert item["payload"]["provider_error"] == "PROVIDER_EXCEPTION"


def test_failed_verification_can_be_marked_rolled_back(tmp_path):
    engine, _ = _engine(tmp_path)
    item = engine.analyze()["results"][0]["suggestion"]
    engine.transition(item["suggestion_id"], "approve", reason="Reviewed")
    failed = engine.transition(item["suggestion_id"], "fail",
                               outcome={"passed": False, "evidence": ["regression test failed"]})
    assert failed["status"] == "FAILED"
    rolled_back = engine.transition(item["suggestion_id"], "rollback",
                                    outcome={"evidence": ["patch reverted", "baseline tests passed"]})
    assert rolled_back["status"] == "ROLLED_BACK"


def test_control_key_auth_rejects_missing_and_accepts_valid_key(monkeypatch):
    from fastapi import HTTPException
    from starlette.requests import Request
    from brain_v12.brain.control_auth import require_control_key

    def request_with(key):
        headers = [] if key is None else [(b"x-brain-control-key", key.encode())]
        scope = {"type": "http", "method": "GET", "path": "/", "headers": headers}
        return Request(scope)

    monkeypatch.setenv("BRAIN_CONTROL_KEY", "test-control-key")
    with pytest.raises(HTTPException) as exc:
        require_control_key(request_with(None))
    assert exc.value.status_code == 403
    require_control_key(request_with("test-control-key"))
