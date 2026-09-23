from pathlib import Path

from brain_v7.braincore_v2.code_tool_engineering_team import CodeToolEngineeringTeam
from brain_v7.braincore_v2.code_workspace_tool import CodeChange, CodeWorkspaceTool
from brain_v7.braincore_v2.employee_hierarchy import EmployeeHierarchy


def test_dedicated_code_tool_team_is_created_and_idempotent():
    org = EmployeeHierarchy()
    workspace = CodeWorkspaceTool(Path.cwd())
    team = CodeToolEngineeringTeam(org, workspace)
    first = set(team.employee_ids)
    assert len(first) == 8
    team2 = CodeToolEngineeringTeam(org, workspace)
    assert set(team2.employee_ids) == first
    assert org.departments["DEPT-CODE-TOOL"].name == "CODE_TOOL_ENGINEERING"


def test_team_plans_work_and_applies_only_validated_changes(tmp_path: Path):
    org = EmployeeHierarchy()
    workspace = CodeWorkspaceTool(tmp_path)
    team = CodeToolEngineeringTeam(org, workspace)
    plan = team.plan_cycle()
    assert plan["employee_count"] == 8
    assert plan["assignments"]

    preview = team.validate_change([CodeChange("tool.py", "VALUE = 7\n")])
    assert preview["status"] == "VALID"
    applied = team.apply_change([CodeChange("tool.py", "VALUE = 7\n")], reason="test")
    assert applied["status"] == "APPLIED"
    assert workspace.read("tool.py") == "VALUE = 7\n"
    assert team.verify(["tool.py"])["status"] == "PASS"


def test_autonomous_change_commits_only_after_regression_pass(monkeypatch, tmp_path: Path):
    org = EmployeeHierarchy()
    workspace = CodeWorkspaceTool(tmp_path)
    team = CodeToolEngineeringTeam(org, workspace)
    monkeypatch.setattr(team, "run_regression_tests", lambda: {"status": "PASS", "returncode": 0})
    monkeypatch.setattr(team.remote, "configured", True, raising=False)
    commits = []
    monkeypatch.setattr(team.remote, "apply", lambda changes, message: commits.append(message) or [])
    result = team.execute_autonomous_change(
        [CodeChange("brain_v7/test_sample.py", "VALUE = 1\n")],
        reason="test",
        commit_message="test: automatic safe change",
        remote=True,
    )
    assert result["status"] == "APPLIED_LOCALLY"
    assert result["regression"]["status"] == "PASS"
    assert commits == ["test: automatic safe change"]


def test_autonomous_change_rolls_back_and_does_not_commit_on_failure(monkeypatch, tmp_path: Path):
    org = EmployeeHierarchy()
    workspace = CodeWorkspaceTool(tmp_path)
    target = tmp_path / "brain_v7" / "test_sample.py"
    target.parent.mkdir(parents=True)
    target.write_text("VALUE = 1\n", encoding="utf-8")
    team = CodeToolEngineeringTeam(org, workspace)
    monkeypatch.setattr(team, "run_regression_tests", lambda: {"status": "FAIL", "returncode": 1})
    commits = []
    monkeypatch.setattr(team.remote, "apply", lambda *args, **kwargs: commits.append(True))
    result = team.execute_autonomous_change(
        [CodeChange("brain_v7/test_sample.py", "VALUE = 2\n")],
        reason="test failure",
        commit_message="test: rejected change",
        remote=True,
    )
    assert result["status"] == "ROLLED_BACK"
    assert target.read_text(encoding="utf-8") == "VALUE = 1\n"
    assert commits == []
