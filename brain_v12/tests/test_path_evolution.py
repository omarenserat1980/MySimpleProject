from brain_v12.brain.path_evolution import PathEvolutionRegistry, PathRecord


def test_best_path_prefers_reliable_then_fast(tmp_path):
    r = PathEvolutionRegistry(tmp_path / "paths.json")
    r.upsert(PathRecord("slow", "scan", ["a"]))
    r.upsert(PathRecord("fast", "scan", ["b"]))
    r.record_run("slow", success=True, seconds=10, evidence="slow-ok")
    r.record_run("slow", success=True, seconds=10, evidence="slow-ok-2")
    r.record_run("fast", success=True, seconds=1, evidence="fast-ok")
    r.record_run("fast", success=False, seconds=1, error="temporary")
    assert r.best("scan").path_id == "slow"


def test_proven_after_two_successes(tmp_path):
    r = PathEvolutionRegistry(tmp_path / "paths.json")
    r.upsert(PathRecord("p", "goal", ["step"]))
    r.record_run("p", success=True)
    assert r.best("goal").status == "candidate"
    r.record_run("p", success=True)
    assert r.best("goal").status == "proven"
