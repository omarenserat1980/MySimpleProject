from pathlib import Path
from brain_v7.braincore_v2.director_scheduler import seed_tasks
from brain_v7.braincore_v2.task_stack import TaskStack
from brain_v7.braincore_v2.take_budget import take_budget

def test_scheduler_keeps_establishing_shots_parallel(tmp_path: Path):
    stack = TaskStack(tmp_path / "tasks.json")
    shots = [
        {"shot_id":"SC01-S01","scene_id":"SC01","generation":{"continuity_policy":"world_first"}},
        {"shot_id":"SC01-S02","scene_id":"SC01","generation":{"continuity_policy":"identity_first"}},
        {"shot_id":"SC01-S03","scene_id":"SC01","generation":{"continuity_policy":"match_cut"}},
        {"shot_id":"SC02-S01","scene_id":"SC02","generation":{"continuity_policy":"world_first"}},
    ]
    seed_tasks(stack, shots)
    ready = {x["task_id"] for x in stack.ready()}
    assert "SC01-S01" in ready
    assert "SC02-S01" in ready
    assert "SC01-S02" not in ready

def test_take_budget_is_adaptive():
    assert take_budget({"purpose":"background","generation":{"continuity_policy":"world_first"}})["max_takes"] == 1
    assert take_budget({"purpose":"Create tension and relevance","duration_s":5,"generation":{"continuity_policy":"identity_first"}})["max_takes"] >= 2
