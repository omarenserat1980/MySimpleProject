from brain_v12.brain.execution_kernel import ExecutionKernel


def test_kernel_fences_stale_worker(tmp_path):
    k = ExecutionKernel(tmp_path / "kernel.json", lease_seconds=60)

    a = k.admit(intent_id="mission-1", operation="boot", owner="brain",
                payload={"vm": "A"}, capacity_admitted=True)
    assert a["status"] == "ADMITTED"
    e = a["envelope"]

    assert k.validate(e["execution_id"], e["epoch"])["ok"] is True

    done = k.finish(e["execution_id"], e["epoch"])
    assert done["ok"] is True

    stale = k.validate(e["execution_id"], e["epoch"])
    assert stale["status"] == "EXECUTION_NOT_ACTIVE"


def test_kernel_increments_fencing_epoch_and_blocks_parallel_execution(tmp_path):
    k = ExecutionKernel(tmp_path / "kernel.json", lease_seconds=60)

    a = k.admit(intent_id="mission-1", operation="run", owner="brain",
                payload={"x": 1})
    assert a["envelope"]["epoch"] == 1

    blocked = k.admit(intent_id="mission-2", operation="run", owner="brain",
                      payload={"x": 2})
    assert blocked["status"] == "EXECUTION_BUSY"

    k.finish(a["envelope"]["execution_id"], a["envelope"]["epoch"])

    b = k.admit(intent_id="mission-2", operation="run", owner="brain",
                payload={"x": 2})
    assert b["status"] == "ADMITTED"
    assert b["envelope"]["epoch"] == 2

    old = k.validate(a["envelope"]["execution_id"], a["envelope"]["epoch"])
    assert old["status"] == "STALE_EXECUTION"


def test_kernel_capacity_gate_is_fail_closed(tmp_path):
    k = ExecutionKernel(tmp_path / "kernel.json")
    result = k.admit(intent_id="mission-1", operation="boot", owner="brain",
                    capacity_admitted=False)
    assert result["status"] == "CAPACITY_BLOCKED"
