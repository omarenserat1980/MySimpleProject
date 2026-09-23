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
