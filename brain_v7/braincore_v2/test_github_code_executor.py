import pytest

from brain_v7.braincore_v2.code_workspace_tool import CodeChange
from brain_v7.braincore_v2.github_code_executor import GitHubCodeExecutor


def test_executor_is_disabled_without_runtime_secret(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    executor = GitHubCodeExecutor(repository="omarenserat1980/MySimpleProject")
    assert executor.configured is False
    with pytest.raises(PermissionError):
        executor.apply([CodeChange("brain_v7/example.py", "VALUE = 1\n")], message="test")


def test_executor_rejects_unsafe_paths(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "test-secret")
    executor = GitHubCodeExecutor(repository="omarenserat1980/MySimpleProject")
    with pytest.raises(PermissionError):
        executor._safe_path(".env")
    with pytest.raises(PermissionError):
        executor._safe_path("../outside.py")
    with pytest.raises(PermissionError):
        executor._safe_path("README.md")


def test_executor_builds_safe_atomic_snapshot(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "test-secret")
    executor = GitHubCodeExecutor(repository="omarenserat1980/MySimpleProject")
    snap = executor.snapshot()
    assert snap["configured"] is True
    assert snap["credential_storage"] is False
    assert snap["token_exposed"] is False
    assert snap["atomic_multi_file_commit"] is True
    assert snap["fast_forward_only"] is True


def test_executor_safe_path_allows_source_files(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "test-secret")
    executor = GitHubCodeExecutor(repository="omarenserat1980/MySimpleProject")
    assert executor._safe_path("brain_v7/braincore_v2/example.py") == "brain_v7/braincore_v2/example.py"
