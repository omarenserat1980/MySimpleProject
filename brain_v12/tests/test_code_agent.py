"""Tests for the reasoning-driven Brain coding agent."""
from pathlib import Path

from brain_v7.braincore_v2.code_workspace_tool import CodeWorkspaceTool
from brain_v7.braincore_v2.code_tool_api import CodeTool
from brain_v7.braincore_v2.code_tool_engineering_team import CodeToolEngineeringTeam
from brain_v7.braincore_v2.employee_hierarchy import EmployeeHierarchy
from brain_v12.brain.code_agent import BrainCodeAgent


class FakeProvider:
    model = "fake"

    def respond(self, user_text, context="", instructions=""):
        return {
            "ok": True,
            "model": self.model,
            "reply": '{"explanation":"safe test change","changes":[{"path":"brain_v7/example.py","content":"VALUE = 2\\n","reason":"test"}]}',
        }


def make_agent(tmp_path: Path):
    (tmp_path / "brain_v7").mkdir()
    (tmp_path / "brain_v7" / "example.py").write_text("VALUE = 1\n", encoding="utf-8")
    ws = CodeWorkspaceTool(tmp_path, allowed_prefixes=("brain_v7/",))
    team = CodeToolEngineeringTeam(EmployeeHierarchy(), ws)
    return BrainCodeAgent(FakeProvider(), CodeTool(ws, team), ws)


def test_plan_returns_preview_without_writing(tmp_path: Path):
    agent = make_agent(tmp_path)
    plan = agent.plan("change value", ["brain_v7/example.py"])
    assert plan["status"] == "PLAN_READY"
    assert (tmp_path / "brain_v7/example.py").read_text() == "VALUE = 1\n"


def test_apply_requires_explicit_approval(tmp_path: Path):
    agent = make_agent(tmp_path)
    plan = agent.plan("change value", ["brain_v7/example.py"])
    result = agent.execute_plan(plan, approved=False, persist_to_github=False)
    assert result["status"] == "EXPLICIT_APPROVAL_REQUIRED"


def test_apply_uses_code_tool_boundary(tmp_path: Path, monkeypatch):
    agent = make_agent(tmp_path)
    monkeypatch.setattr(agent.tool.team, "run_regression_tests", lambda: {
        "status": "PASS", "returncode": 0, "command": [], "stdout_tail": "", "stderr_tail": ""
    })
    plan = agent.plan("change value", ["brain_v7/example.py"])
    result = agent.execute_plan(plan, approved=True, persist_to_github=False)
    assert result["status"] == "APPLIED_LOCALLY"
    assert (tmp_path / "brain_v7/example.py").read_text() == "VALUE = 2\n"
