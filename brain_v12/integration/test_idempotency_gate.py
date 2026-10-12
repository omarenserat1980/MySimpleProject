import pytest
from brain_v12.integration.idempotency_gate import ExecutionIntent,IdempotencyGate

def intent():
    return ExecutionIntent("a"*64,"publish","p"*64)

def test_same_intent_has_same_key():
    i=intent()
    assert i.execution_key==intent().execution_key
    assert len(i.execution_key)==64

def test_duplicate_claim_is_blocked():
    g=IdempotencyGate(); i=intent()
    g.claim(i)
    with pytest.raises(RuntimeError):
        g.claim(i)

def test_completed_execution_cannot_repeat():
    g=IdempotencyGate(); i=intent()
    g.claim(i); g.complete(i)
    assert g.is_completed(i)
    with pytest.raises(RuntimeError):
        g.claim(i)

def test_completion_requires_claim():
    g=IdempotencyGate()
    with pytest.raises(RuntimeError):
        g.complete(intent())
