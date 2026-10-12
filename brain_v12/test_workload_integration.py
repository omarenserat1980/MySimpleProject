from brain_v12.brain.workload_controller import WorkloadController
from brain_v12.brain.workload_router import WorkloadRouter, WorkerTarget

def test_cloud_preferred_over_github():
    d=WorkloadRouter().choose(queued=10,active=1,required_capabilities={"python"},workers=[
        WorkerTarget("gha","github",frozenset({"python","ci"})),
        WorkerTarget("cloud","cloud",frozenset({"python"}))])
    assert d["route"]["worker_id"]=="cloud"

def test_emergency_blocks_background():
    d=WorkloadRouter().choose(queued=800,active=1,priority="BACKGROUND",workers=[])
    assert not d["admit"]

def test_virtual_queue_contains_admission_gate():
    assert "self.workload_router.choose" in open("brain_v12/brain/virtual_task_queue.py").read()
