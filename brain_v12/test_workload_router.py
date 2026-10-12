from brain_v12.brain.workload_controller import WorkloadController
from brain_v12.brain.workload_router import WorkloadRouter,WorkerTarget

def test_routes_heavy_work_to_cloud():
    r=WorkloadRouter().choose(queued=10,active=1,required_capabilities={"python"},workers=[
        WorkerTarget("github-actions","github",frozenset({"python","ci"})),
        WorkerTarget("cloud-01","cloud",frozenset({"python"})),
    ])
    assert r["route"]["worker_id"]=="cloud-01"

def test_falls_back_to_github_for_ci():
    r=WorkloadRouter().choose(queued=10,active=1,required_capabilities={"ci"},workers=[])
    assert r["route"]["kind"]=="github"

def test_emergency_rejects_background():
    r=WorkloadRouter().choose(queued=800,active=1,priority="BACKGROUND",workers=[])
    assert not r["admit"]
