from brain_v12.self_healing.deep_execution_orchestrator import DeepExecutionOrchestrator
from brain_v12.self_healing.deep_execution_engine import Operation

def test_orchestrator_selects_depth(tmp_path):
    def execute(op):
        return {"status": "VERIFIED"}
    o = DeepExecutionOrchestrator(execute, str(tmp_path))
    state = o.run_until_gate([Operation(str(i), "check") for i in range(20)])
    assert state["depth"] == 2
    assert state["depth_gate"]["promoted"] is False
