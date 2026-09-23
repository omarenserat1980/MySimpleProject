from pathlib import Path

from brain_v7.braincore_v2.code_evolution_controller import CodeEvolutionController
from brain_v7.braincore_v2.code_tool_engineering_team import CodeToolEngineeringTeam
from brain_v7.braincore_v2.code_workspace_tool import CodeChange, CodeWorkspaceTool
from brain_v7.braincore_v2.employee_hierarchy import EmployeeHierarchy


def test_code_evolution_records_tested_lifecycle(monkeypatch, tmp_path: Path):
    org = EmployeeHierarchy()
    workspace = CodeWorkspaceTool(tmp_path)
    team = CodeToolEngineeringTeam(org, workspace)
    monkeypatch.setattr(team, "run_regression_tests", lambda: {"status": "PASS", "returncode": 0})
    controller = CodeEvolutionController(team)

    result = controller.execute(
        [CodeChange("brain_v7/improvement.py", "VALUE = 1\n")],
        objective="add a safe improvement",
        persist_to_github=False,
    )

    assert result["status"] == "TESTED"
    assert workspace.read("brain_v7/improvement.py") == "VALUE = 1\n"
    assert result["job"]["status"] == "TESTED"


def test_code_evolution_rolls_back_failed_regression(monkeypatch, tmp_path: Path):
    org = EmployeeHierarchy()
    workspace = CodeWorkspaceTool(tmp_path)
    target = tmp_path / "brain_v7" / "sample.py"
    target.parent.mkdir(parents=True)
    target.write_text("VALUE = 1\n", encoding="utf-8")
    team = CodeToolEngineeringTeam(org, workspace)
    monkeypatch.setattr(team, "run_regression_tests", lambda: {"status": "FAIL", "returncode": 1})
    controller = CodeEvolutionController(team)

    result = controller.execute(
        [CodeChange("brain_v7/sample.py", "VALUE = 2\n")],
        objective="reject an unsafe regression",
        persist_to_github=False,
    )

    assert result["status"] == "ROLLED_BACK"
    assert target.read_text(encoding="utf-8") == "VALUE = 1\n"
