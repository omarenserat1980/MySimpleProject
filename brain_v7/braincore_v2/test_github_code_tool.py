from brain_v7.braincore_v2.github_code_tool import GitHubCodeTool


def test_plan_and_apply():
    calls = []

    def fetch(path):
        return {"path": path, "sha": "abc"}

    def update(repo, path, content, message, sha):
        calls.append((repo, path, content, message, sha))
        return {"result": {"commit_sha": "commit1", "content_sha": "blob1"}}

    tool = GitHubCodeTool(fetch, update)
    change = tool.plan("brain_v7/example.py", "print('ok')\n", "abc", "update example")
    result = tool.apply(change)

    assert result.status == "APPLIED"
    assert result.commit_sha == "commit1"
    assert calls[0][0] == "omarenserat1980/MySimpleProject"


def test_secret_paths_are_rejected():
    tool = GitHubCodeTool(lambda p: {}, lambda *a: {})
    try:
        tool.plan(".github/workflows/secret.py", "x", "sha", "msg")
    except PermissionError as exc:
        assert "path_not_allowed" in str(exc)
    else:
        raise AssertionError("secret path should be rejected")


def test_oauth_is_not_stored():
    tool = GitHubCodeTool(lambda p: {}, lambda *a: {})
    assert tool.snapshot()["oauth_secret_storage"] is False
