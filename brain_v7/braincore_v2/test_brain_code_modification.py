from pathlib import Path

from brain_v7.braincore_v2.brain_orchestrator import UnifiedBrain
from brain_v7.braincore_v2.code_workspace_tool import CodeChange, CodeWorkspaceTool


def test_brain_exposes_bounded_self_modification(tmp_path: Path, monkeypatch):
    brain = UnifiedBrain(initial_employees=1)
    brain.code_workspace = CodeWorkspaceTool(tmp_path)
    brain.code_tool_team.workspace = brain.code_workspace
    monkeypatch.setattr(brain.code_tool_team, "run_regression_tests", lambda: {"status": "PASS", "returncode": 0})
    monkeypatch.setattr(brain.code_tool_team.remote, "configured", False, raising=False)

    result = brain.self_modify_code(
        [CodeChange("brain_v7/demo.py", "VALUE = 42\\n", "safe self-modification test")],
        reason="test bounded coding tool",
        commit_message="test: bounded self modification",
        remote=False,
    )
    assert result["status"] == "APPLIED_LOCALLY"
    assert brain.code_workspace.read("brain_v7/demo.py") == "VALUE = 42\\n"
    assert result["regression"]["status"] == "PASS"


def test_brain_self_modification_rolls_back_on_regression_failure(tmp_path: Path, monkeypatch):
    brain = UnifiedBrain(initial_employees=1)
    brain.code_workspace = CodeWorkspaceTool(tmp_path)
    brain.code_tool_team.workspace = brain.code_workspace
    target = tmp_path / "brain_v7" / "demo.py"
    target.parent.mkdir(parents=True)
    target.write_text("VALUE = 1\\n", encoding="utf-8")
    monkeypatch.setattr(brain.code_tool_team, "run_regression_tests", lambda: {"status": "FAIL", "returncode": 1})

    result = brain.self_modify_code(
        [CodeChange("brain_v7/demo.py", "VALUE = 2\\n")],
        reason="failure rollback test",
        commit_message="test: rollback",
        remote=False,
    )
    assert result["status"] == "ROLLED_BACK"
    assert target.read_text(encoding="utf-8") == "VALUE = 1\\n"
