from brain_v12.brain.task_envelope import TaskEnvelope


def test_valid_envelope_serializes_without_executing():
    envelope = TaskEnvelope(1, "task-1", "idem-1", "sha256:abc", ("cpu",), "local-test", "0", {"op": "inspect"})
    result = envelope.to_dict()
    assert result["valid"] is True
    assert result["execution_performed"] is False


def test_nonzero_cost_and_missing_idempotency_are_rejected():
    envelope = TaskEnvelope(1, "task-2", "", "", ("cpu",), "scope", "0.01", {})
    errors = envelope.validate()
    assert "IDEMPOTENCY_KEY_REQUIRED" in errors
    assert "INTENT_HASH_REQUIRED" in errors
    assert "NONZERO_OR_UNCONFIRMED_COST_BLOCKED" in errors


def test_unknown_schema_is_rejected():
    envelope = TaskEnvelope(2, "task-3", "idem", "hash", ("cpu",), "scope", "0", {})
    assert "SCHEMA_VERSION_UNSUPPORTED" in envelope.validate()
