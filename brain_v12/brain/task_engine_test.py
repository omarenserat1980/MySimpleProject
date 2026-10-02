from brain_v12.brain.task_engine import TaskEngine

def test_completion_requires_evidence():
    engine=TaskEngine()
    task=engine.create("repair customer issue")
    assert engine.update(task["id"], "COMPLETED")["error"] == "EVIDENCE_REQUIRED"
    completed=engine.update(task["id"], "COMPLETED", "test://verified")
    assert completed["status"] == "COMPLETED"
    assert completed["evidence_ref"] == "test://verified"
