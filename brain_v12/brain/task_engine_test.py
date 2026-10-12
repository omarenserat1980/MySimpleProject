import json
import os

from brain_v12.brain.task_engine import TaskEngine


def test_completion_requires_evidence():
    engine = TaskEngine()
    task = engine.create("repair customer issue")
    assert engine.update(task["id"], "COMPLETED")["error"] == "EVIDENCE_REQUIRED"
    completed = engine.update(task["id"], "COMPLETED", "test://verified")
    assert completed["status"] == "COMPLETED"
    assert completed["evidence_ref"] == "test://verified"


def test_verify_and_complete_requires_pass_and_evidence():
    engine = TaskEngine()
    task = engine.create("verified repair")
    assert engine.verify_and_complete(task["id"], False, "test://failed")["error"] == "VERIFICATION_FAILED"
    assert engine.verify_and_complete(task["id"], True)["error"] == "EVIDENCE_REQUIRED"
    done = engine.verify_and_complete(task["id"], True, "test://verified")
    assert done["status"] == "COMPLETED"
    assert done["evidence_ref"] == "test://verified"


def test_verify_and_complete_rejects_truthy_failed_mapping():
    engine = TaskEngine()
    task = engine.create("failed verification")
    result = engine.verify_and_complete(
        task["id"],
        {"ok": False, "verified": False, "status": "FAILED"},
        "test://failed",
    )
    assert result["error"] == "VERIFICATION_FAILED"
    assert task["status"] == "PENDING"


def test_failed_task_preserves_evidence_and_retry_lineage():
    engine = TaskEngine()
    task = engine.create("retryable repair")
    failed = engine.fail(task["id"], "TEST_FAILURE", "test://failure")
    assert failed["evidence_ref"] == "test://failure"
    retried = engine.retry(task["id"])
    assert retried["ok"] is True
    assert retried["task"]["retry_of"] == task["id"]
    assert retried["task"]["retry_count"] == 1


def test_failed_task_emits_diagnostic_evidence(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAIN_EVIDENCE_DIR", str(tmp_path))
    engine = TaskEngine()
    task = engine.create("diagnostic failure")
    failed = engine.fail(task["id"], "TEST_DIAGNOSTIC_FAILURE")
    ref = failed["diagnostic_evidence_ref"]
    assert ref.startswith(str(tmp_path))
    with open(ref, encoding="utf-8") as handle:
        payload = json.load(handle)
    assert payload["schema"] == "brain.task_failure_diagnostic.v1"
    assert payload["error"] == "TEST_DIAGNOSTIC_FAILURE"
    assert payload["task"]["id"] == task["id"]
    assert payload["task"]["status"] == "FAILED"
