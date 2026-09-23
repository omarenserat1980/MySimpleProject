from pathlib import Path

import pytest

from brain_v7.braincore_v2.code_workspace_tool import CodeChange, CodeWorkspaceTool


def test_apply_is_atomic_and_validates_python(tmp_path: Path):
    tool = CodeWorkspaceTool(tmp_path)
    result = tool.apply([
        CodeChange("hello.py", "VALUE = 42\n", "test change"),
    ])
    assert result[0].status == "APPLIED"
    assert (tmp_path / "hello.py").read_text() == "VALUE = 42\n"
    assert tool.read("hello.py") == "VALUE = 42\n"


def test_invalid_python_rolls_back_transaction(tmp_path: Path):
    (tmp_path / "good.py").write_text("VALUE = 1\n")
    tool = CodeWorkspaceTool(tmp_path)
    with pytest.raises(SyntaxError):
        tool.apply([
            CodeChange("good.py", "VALUE = 2\n"),
            CodeChange("bad.py", "def broken(:\n"),
        ])
    assert (tmp_path / "good.py").read_text() == "VALUE = 1\n"
    assert not (tmp_path / "bad.py").exists()


def test_workspace_rejects_escape_and_protected_files(tmp_path: Path):
    tool = CodeWorkspaceTool(tmp_path)
    with pytest.raises(ValueError):
        tool.read("../outside.py")
    with pytest.raises(PermissionError):
        tool.read(".env")


def test_dry_run_diff_checkpoint_restore(tmp_path: Path):
    tool = CodeWorkspaceTool(tmp_path)
    tool.apply([CodeChange("app.py", "VALUE = 1\n")])
    preview = tool.dry_run([CodeChange("app.py", "VALUE = 2\n")])
    assert preview["status"] == "VALID"
    assert preview["writes"] == 0
    assert tool.read("app.py") == "VALUE = 1\n"
    diff = tool.diff([CodeChange("app.py", "VALUE = 2\n")])
    assert diff[0]["changed"] is True

    checkpoint = tool.checkpoint(["app.py"])
    tool.apply([CodeChange("app.py", "VALUE = 99\n")])
    assert tool.read("app.py") == "VALUE = 99\n"
    restored = tool.restore(checkpoint["checkpoint_id"])
    assert restored[0].status == "APPLIED"
    assert tool.read("app.py") == "VALUE = 1\n"
    assert tool.verify(["app.py"])["status"] == "PASS"


def test_checkpoint_rejects_path_injection(tmp_path: Path):
    tool = CodeWorkspaceTool(tmp_path)
    with pytest.raises(ValueError):
        tool.restore("../cp-bad")


def test_workspace_allowlist_blocks_other_source_tree(tmp_path: Path):
    tool = CodeWorkspaceTool(tmp_path, allowed_prefixes=("brain_v7/",))
    (tmp_path / "brain_v7").mkdir()
    tool.apply([CodeChange("brain_v7/allowed.py", "VALUE = 1\n")])
    assert tool.read("brain_v7/allowed.py") == "VALUE = 1\n"
    with pytest.raises(PermissionError):
        tool.read("other.py")


def test_code_tool_api_exposes_save_and_restore(tmp_path: Path):
    from brain_v7.braincore_v2.code_tool_api import CodeTool
    from brain_v7.braincore_v2.code_tool_engineering_team import CodeToolEngineeringTeam
    from brain_v7.braincore_v2.employee_hierarchy import EmployeeHierarchy

    workspace = CodeWorkspaceTool(tmp_path)
    team = CodeToolEngineeringTeam(EmployeeHierarchy(initial_employees=0), workspace)
    api = CodeTool(workspace, team)
    api.execute([CodeChange("brain_v7/api_test.py", "VALUE = 1\\n")], reason="test", commit_message="test: seed", persist_to_github=False)
    checkpoint = api.save_checkpoint(["brain_v7/api_test.py"])
    api.execute([CodeChange("brain_v7/api_test.py", "VALUE = 2\\n")], reason="test", commit_message="test: update", persist_to_github=False)
    restored = api.restore_checkpoint(checkpoint["checkpoint_id"])
    assert restored["status"] == "RESTORED"
    assert workspace.read("brain_v7/api_test.py") == "VALUE = 1\\n"
