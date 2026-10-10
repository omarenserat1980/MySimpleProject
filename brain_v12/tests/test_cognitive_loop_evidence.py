from brain_v12.brain.cognitive_loop import CognitiveLoop


class MemoryStore:
    def __init__(self):
        self._state = {}
        self._memories = []
        self.events = []

    def state(self):
        return dict(self._state)

    def set_state(self, state):
        self._state = dict(state)

    def memories(self):
        return list(self._memories)

    def save_memory(self, key, value):
        self._memories.append({"key": key, "value": value})

    def event(self, event_type, payload=None):
        self.events.append({"type": event_type, "payload": payload or {}})


def test_cognitive_loop_completes_only_with_evidence():
    store = MemoryStore()
    loop = CognitiveLoop(store)

    result = loop.run("review current state safely")

    assert result["execution"]["status"] == "COMPLETED"
    assert result["execution"]["evidence_ref"].startswith("cognitive://")
    assert result["verification"]["result_verified"] is True
    assert result["learning"]["status"] == "RECORDED"
    assert result["learning"]["lesson"]["verified"] is True
    task = next(
        task for task in result["tasks"]["tasks"]
        if task["id"] == result["execution"]["task_id"]
    )
    assert task["status"] == "COMPLETED"
    assert task["evidence_ref"] == result["execution"]["evidence_ref"]


def test_cognitive_loop_does_not_complete_when_tool_fails():
    store = MemoryStore()
    loop = CognitiveLoop(store)
    loop.execute_tool = lambda *args, **kwargs: {
        "ok": False, "status": "UNAVAILABLE", "tool": "memory.read"
    }

    result = loop.run("review current state safely")

    assert result["execution"]["status"] == "FAILED"
    assert result["verification"]["result_verified"] is False
    assert result["learning"]["lesson"]["verified"] is False
    task = next(
        task for task in result["tasks"]["tasks"]
        if task["id"] == result["execution"]["task_id"]
    )
    assert task["status"] == "PENDING"
