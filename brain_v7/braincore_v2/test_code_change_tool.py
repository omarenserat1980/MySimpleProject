from brain_v7.braincore_v2.code_change_tool import CodeChange, CodeChangeTool


def test_prepare_and_block_secrets():
    tool = CodeChangeTool()
    change = CodeChange(
        path="brain_v7/braincore_v2/example.py",
        content="print('ok')\n",
        reason="test change",
    )
    prepared = tool.prepare(change)
    assert prepared["action"] == "UPDATE_OR_CREATE"
    assert len(prepared["content_sha256"]) == 64

    try:
        tool.prepare(CodeChange(
            path="brain_v7/braincore_v2/.env",
            content="SECRET=x",
            reason="should fail",
        ))
    except ValueError:
        pass
    else:
        raise AssertionError("secret files must be blocked")


def test_workspace_executor_writes_and_blocks_push_by_default(tmp_path):
    from brain_v7.braincore_v2.code_change_tool import WorkspaceCodeExecutor
    tool = WorkspaceCodeExecutor(str(tmp_path))
    result = tool.apply(CodeChange(
        path="brain_v7/braincore_v2/demo.py",
        content="VALUE = 7\n",
        reason="executor test",
    ))
    assert result.ok
    assert (tmp_path / "brain_v7/braincore_v2/demo.py").read_text() == "VALUE = 7\n"
    pushed = tool.push()
    assert not pushed.ok
