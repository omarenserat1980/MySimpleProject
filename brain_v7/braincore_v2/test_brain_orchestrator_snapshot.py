from brain_v7.braincore_v2.brain_orchestrator import build_brain


def test_snapshot_includes_youtube_pipeline_without_undefined_reference():
    brain = build_brain(initial_employees=0)
    snapshot = brain.snapshot()
    assert "youtube_team" in snapshot
    assert "youtube_pipeline" in snapshot
    assert snapshot["youtube_pipeline"] == snapshot["youtube_team"]
