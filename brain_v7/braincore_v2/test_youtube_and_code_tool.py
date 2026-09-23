from brain_v7.braincore_v2.brain_orchestrator import UnifiedBrain
from brain_v7.braincore_v2.code_workspace_tool import CodeChange


def test_youtube_team_has_exactly_twenty_specialists():
    brain = UnifiedBrain()
    snap = brain.youtube_team.snapshot()
    assert snap["employee_count"] == 20
    assert snap["target_employee_count"] == 20
    assert snap["publishing_requires_authorization"] is True


def test_code_tool_can_dry_run_a_safe_python_change():
    brain = UnifiedBrain()
    result = brain.code_tool_team.validate_change([
        CodeChange(
            "brain_v7/braincore_v2/_brain_tool_test_probe.py",
            "VALUE = 1\n",
            "test only",
        )
    ])
    assert result["status"] == "VALID"
    assert result["writes"] == 0


def test_brain_exposes_code_persistence_and_youtube_team():
    brain = UnifiedBrain()
    snap = brain.snapshot()
    assert snap["youtube_team"]["employee_count"] == 20
    assert snap["code_tool_engineering"]["capability_status"]["save_source"] is True
    assert snap["code_tool_engineering"]["capability_status"]["checkpoint_and_rollback"] is True
