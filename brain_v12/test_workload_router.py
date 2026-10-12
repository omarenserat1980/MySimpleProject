from brain_v12.brain.workload_router import WorkloadRouter, WorkerTarget


def test_routes_heavy_work_to_cloud():
    result = WorkloadRouter().choose(
        queued=10, active=1, required_capabilities={"python"},
        workers=[
            WorkerTarget("github-actions", "github", frozenset({"python", "ci"})),
            WorkerTarget("cloud-01", "cloud", frozenset({"python"})),
        ],
    )
    assert result["route"]["worker_id"] == "cloud-01"


def test_falls_back_to_github_only_when_explicitly_available():
    result = WorkloadRouter().choose(
        queued=10, active=1, required_capabilities={"ci"}, workers=[],
        github_available=True,
    )
    assert result["route"]["kind"] == "github"


def test_missing_github_runner_is_capacity_block_not_success():
    result = WorkloadRouter().choose(
        queued=10, active=1, required_capabilities={"ci"}, workers=[],
    )
    assert result["ok"] is True
    assert result["admit"] is False
    assert result["route"] is None
    assert result["reason"] == "NO_WORKER_AVAILABLE"


def test_offline_worker_does_not_satisfy_capability():
    result = WorkloadRouter().choose(
        queued=10, active=1, required_capabilities={"python"},
        workers=[WorkerTarget("offline", "cloud", frozenset({"python"}), False)],
        github_available=False,
    )
    assert result["admit"] is False
    assert result["reason"] == "NO_WORKER_AVAILABLE"


def test_emergency_rejects_background():
    result = WorkloadRouter().choose(
        queued=800, active=1, priority="BACKGROUND", workers=[],
    )
    assert not result["admit"]
