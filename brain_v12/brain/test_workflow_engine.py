import time
from brain_v12.brain_git.workflow_engine import BrainWorkflowEngine


class TestExecutionGateway:
    def run(self, command, capability, cwd=None, timeout=None):
        assert command == ["python", "-c", "print('ok')"]
        return {
            "ok": True,
            "stdout": "ok\n",
            "stderr": "",
            "returncode": 0,
            "executor": "test-gateway",
            "authority": "test",
            "verified_executor": True,
        }


def test_workflow_has_event_history_and_heartbeat(tmp_path):
    e=BrainWorkflowEngine(tmp_path, execution_gateway=TestExecutionGateway())
    x=e.create("t", ["python", "-c", "print('ok')"], metadata={"idempotency_key":"k1"})
    assert x["status"]=="QUEUED"
    assert x["events"][0]["event"]=="CREATED"
    y=e.run(x)
    assert y["status"]=="SUCCESS"
    assert y["heartbeat_at"] is not None
    assert any(ev["event"]=="FINISHED" for ev in y["events"])


def test_idempotency_reuses_workflow(tmp_path):
    e=BrainWorkflowEngine(tmp_path)
    a=e.create("t", ["true"], metadata={"idempotency_key":"same"})
    b=e.create("t2", ["false"], metadata={"idempotency_key":"same"})
    assert a["id"]==b["id"]


def test_stale_running_workflow_recovery(tmp_path):
    e=BrainWorkflowEngine(tmp_path, lease_seconds=10)
    x=e.create("t", ["true"])
    x["status"]="RUNNING"; x["heartbeat_at"]=time.time()-20
    e._save(x)
    recovered=e.recover_stale()
    assert recovered[0]["status"]=="QUEUED"
    assert any(ev["event"]=="STALE_RECOVERED" for ev in recovered[0]["events"])
