"""Focused regression tests for the adaptive cinematic factory."""
from brain_v7.braincore_v2.task_stack import TaskStack
from brain_v7.braincore_v2.director_scheduler import seed_tasks
from brain_v7.braincore_v2.final_film_qc import evaluate_final_film

def test_task_dependencies():
    stack=TaskStack(":memory-not-used:")
    shots=[{"shot_id":"shot_001","scene_id":1},{"shot_id":"shot_002","scene_id":1}]
    seed_tasks(stack,shots)
    assert [x["task_id"] for x in stack.ready()]==["shot_001"]
    stack.complete("shot_001")
    assert [x["task_id"] for x in stack.ready()]==["shot_002"]

def test_final_qc_detects_missing():
    manifest={"shots":[{"shot_id":"shot_001"},{"shot_id":"shot_002"}]}
    result=evaluate_final_film(manifest,[{"shot_id":"shot_001","status":"VERIFIED_COMPLETED"}])
    assert result["status"]=="REPAIR"
    assert result["missing"]==["shot_002"]
