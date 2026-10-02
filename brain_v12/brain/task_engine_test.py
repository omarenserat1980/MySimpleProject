from brain_v12.brain.task_engine import TaskEngine

def test_completion_requires_evidence():
    engine=TaskEngine()
    task=engine.create("repair customer issue")
    assert engine.update(task["id"], "COMPLETED")["error"] == "EVIDENCE_REQUIRED"
    completed=engine.update(task["id"], "COMPLETED", "test://verified")
    assert completed["status"] == "COMPLETED"
    assert completed["evidence_ref"] == "test://verified"

def test_verify_and_complete_requires_pass_and_evidence():
    engine=TaskEngine()
    task=engine.create("verified repair")
    assert engine.verify_and_complete(task["id"], False, "test://failed")["error"] == "VERIFICATION_FAILED"
    assert engine.verify_and_complete(task["id"], True)["error"] == "EVIDENCE_REQUIRED"
    done=engine.verify_and_complete(task["id"], True, "test://verified")
    assert done["status"] == "COMPLETED"
    assert done["evidence_ref"] == "test://verified"

def test_failed_task_preserves_evidence_and_retry_lineage():
    engine=TaskEngine()
    task=engine.create("retryable repair")
    failed=engine.fail(task["id"], "TEST_FAILURE", "test://failure")
    assert failed["evidence_ref"] == "test://failure"
    retried=engine.retry(task["id"])
    assert retried["ok"] is True
    assert retried["task"]["retry_of"] == task["id"]
    assert retried["task"]["retry_count"] == 1
