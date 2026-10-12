from brain_v12.self_healing.deep_execution_engine import (
    DeepExecutionEngine, DeepExecutionPolicy, Operation, depth_for,
)

def test_depth_budget_mapping():
    assert depth_for(1) == 0
    assert depth_for(20) == 2
    assert depth_for(100) == 4

def test_checkpoint_and_dedup(tmp_path):
    seen = []
    def execute(op):
        seen.append(op.op_id)
        return {"status": "VERIFIED"}

    engine = DeepExecutionEngine(
        tmp_path,
        DeepExecutionPolicy(depth=2, checkpoint_every=1),
        execute,
    )
    ops = [Operation("a", "check"), Operation("b", "repair")]
    first = engine.run(ops)
    assert first["last_run"]["executed"] == 2
    second = engine.run(ops)
    assert second["last_run"]["skipped"] == 2
    assert seen == ["a", "b"]
