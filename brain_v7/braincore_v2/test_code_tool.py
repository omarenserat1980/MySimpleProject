"""Regression tests for the bounded code persistence tool."""
from pathlib import Path

from brain_v7.braincore_v2.code_workspace_tool import CodeChange, CodeWorkspaceTool
from brain_v7.braincore_v2.github_code_executor import GitHubCodeExecutor


def test_workspace_dry_run_apply_and_rollback(tmp_path: Path):
    workspace = CodeWorkspaceTool(tmp_path)
    change = CodeChange("brain_v7/example.py", "VALUE = 42\n")
    preview = workspace.dry_run([change])
    assert preview["status"] == "VALID"
    result = workspace.apply([change])
    assert result[0].status == "APPLIED"
    assert (tmp_path / "brain_v7/example.py").read_text() == "VALUE = 42\n"
    checkpoint = workspace.checkpoint(["brain_v7/example.py"])
    workspace.apply([CodeChange("brain_v7/example.py", "VALUE = 99\n")])
    workspace.restore(checkpoint["checkpoint_id"])
    assert (tmp_path / "brain_v7/example.py").read_text() == "VALUE = 42\n"


def test_workspace_blocks_credentials_and_path_escape(tmp_path: Path):
    workspace = CodeWorkspaceTool(tmp_path)
    for path in (".env", "credentials.json", "../escape.py"):
        try:
            workspace.dry_run([CodeChange(path, "x = 1\n")])
        except (PermissionError, ValueError):
            pass
        else:
            raise AssertionError(f"unsafe path was accepted: {path}")


def test_github_executor_requires_runtime_configuration(monkeypatch):
    monkeypatch.delenv("BRAIN_GITHUB_REPOSITORY", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    executor = GitHubCodeExecutor()
    assert executor.configured is False
    snapshot = executor.snapshot()
    assert snapshot["token_exposed"] is False
    assert snapshot["delete_supported"] is False
