from brain_v12.brain.operation_engine import OperationEngine


class Store:
    def __init__(self):
        self.events = []

    def event(self, kind, payload):
        self.events.append((kind, payload))


def test_build_creates_prompt_and_audit_event():
    store = Store()
    engine = OperationEngine(store)
    op = engine.build("RENDER", "recover the current service")
    assert op["status"] == "READY"
    assert "RENDER" in op["auto_prompt"]
    assert "Do not create a new service" in op["auto_prompt"]
    assert store.events[0][0] == "OPERATION_CREATED"


def test_human_gate_pauses_without_executor():
    store = Store()
    engine = OperationEngine(store)
    op = engine.build("DEVICE", "run a sensitive action", human_gate=True)
    result = engine.run(op)
    assert result["status"] == "AWAITING_APPROVAL"
    assert any(kind == "OPERATION_HUMAN_GATE" for kind, _ in store.events)


def test_executor_retries_and_verifies():
    store = Store()
    engine = OperationEngine(store)
    attempts = {"n": 0}

    def executor(_):
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise RuntimeError("temporary")
        return {"verified": True, "value": "ok"}

    engine.register_executor("TEST", executor)
    op = engine.build("TEST", "run a deterministic operation", retry_limit=1)
    result = engine.run(op)
    assert result["status"] == "SUCCESS"
    assert result["attempts"] == 2
    assert any(kind == "OPERATION_VERIFIED" for kind, _ in store.events)


def test_missing_executor_is_blocked():
    store = Store()
    engine = OperationEngine(store)
    op = engine.build("GITHUB", "inspect repository")
    result = engine.run(op)
    assert result["status"] == "BLOCKED"
    assert result["error"] == "NO_EXECUTOR_REGISTERED"
