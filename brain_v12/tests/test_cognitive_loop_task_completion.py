import tempfile

from brain_v12.brain.cognitive_loop import CognitiveLoop
from brain_v12.brain.memory import MemoryStore


def make_loop():
    handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    handle.close()
    store = MemoryStore(handle.name)
    store.init()
    return CognitiveLoop(store)


def test_tasks_complete_does_not_report_success_without_evidence():
    loop = make_loop()
    task = loop.tasks.create("evidence-gated completion")

    result = loop.execute_tool("tasks.complete", {"task_id": task["id"]})

    assert result["ok"] is False
    assert result["status"] == "EVIDENCE_REQUIRED"
    assert result["data"]["error"] == "EVIDENCE_REQUIRED"
    assert loop.tasks.snapshot()["tasks"][0]["status"] == "PENDING"


def test_tasks_complete_reports_success_when_evidence_is_supplied():
    loop = make_loop()
    task = loop.tasks.create("verified completion")

    result = loop.execute_tool(
        "tasks.complete",
        {"task_id": task["id"], "evidence_ref": "test://verified"},
    )

    assert result["ok"] is True
    assert result["status"] == "COMPLETED"
    assert result["data"]["evidence_ref"] == "test://verified"
    assert loop.tasks.snapshot()["tasks"][0]["status"] == "COMPLETED"
