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
