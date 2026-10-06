from brain_v12.self_healing.deep_execution_bridge import SupervisorDeepExecutionBridge
from brain_v12.self_healing.deep_execution_engine import Operation

class Supervisor:
    def __init__(self): self.phases = []
    def transition(self, job, phase, status="running", details=None, **kwargs):
        self.phases.append((phase, status, details or {}))
        return job

def test_bridge_batches_once(tmp_path):
    s = Supervisor()
    b = SupervisorDeepExecutionBridge(s, lambda op: {"status": "VERIFIED"}, str(tmp_path))
    job = {"job_id": "j1"}
    result = b.execute_batch(job, [Operation("1", "check"), Operation("2", "verify")])
    assert result["status"] == "completed"
    assert result["depth"] == 1
    assert [x[0] for x in s.phases] == ["execute", "verify"]
