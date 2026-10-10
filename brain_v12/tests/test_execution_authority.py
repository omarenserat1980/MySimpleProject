from brain_v12.brain.execution_authority import ExecutionAuthority


def test_single_active_execution_and_idempotency(tmp_path):
    authority = ExecutionAuthority(tmp_path / "state.json", lease_seconds=60, max_active=1)

    first = authority.acquire(
        intent_id="i1", operation="boot", owner="supervisor",
        payload={"vm": "brain"}, capacity_admitted=True,
    )
    assert first["ok"] is True
    assert first["status"] == "ADMITTED"

    same = authority.acquire(
        intent_id="i1", operation="boot", owner="supervisor",
        payload={"vm": "brain"}, capacity_admitted=True,
    )
    assert same["status"] == "IDEMPOTENT_REUSE"

    blocked = authority.acquire(
        intent_id="i2", operation="boot", owner="supervisor",
        payload={"vm": "other"}, capacity_admitted=True,
    )
    assert blocked["status"] == "EXECUTION_BUSY"


def test_capacity_gate_and_release(tmp_path):
    authority = ExecutionAuthority(tmp_path / "state.json")
    denied = authority.acquire(
        intent_id="i1", operation="boot", owner="supervisor",
        capacity_admitted=False,
    )
    assert denied["status"] == "CAPACITY_BLOCKED"

    lease = authority.acquire(
        intent_id="i1", operation="boot", owner="supervisor",
        capacity_admitted=True,
    )["lease"]
    released = authority.release(lease["lease_id"], "COMPLETED")
    assert released["ok"] is True
    assert authority.status()["active_count"] == 0
