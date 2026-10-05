from platform_foundation.github_code_agent import GitHubCodeAgent


def test_agent_requires_real_change_and_commits_only_after_verification():
    files={"x.py":"old"}
    committed=[]
    agent=GitHubCodeAgent(
        read=lambda target: files[target],
        test=lambda: True,
        commit=lambda target, message: committed.append((target,message)) or "abc123",
    )
    plan=agent.prepare(target="x.py",proposed_content="new",description="safe change")
    result=agent.execute(plan,apply=lambda p: files.__setitem__(p.target,"new"),verify=lambda p: files[p.target]=="new")
    assert result.committed is True
    assert result.verified is True
    assert result.commit_sha=="abc123"


def test_agent_does_not_commit_when_tests_fail():
    files={"x.py":"old"}
    committed=[]
    agent=GitHubCodeAgent(read=lambda target: files[target],test=lambda: False,commit=lambda *a: committed.append(a) or "bad")
    plan=agent.prepare(target="x.py",proposed_content="new",description="unsafe until tests pass")
    result=agent.execute(plan,apply=lambda p: files.__setitem__(p.target,"new"),verify=lambda p: True)
    assert result.committed is False
    assert committed==[]


def test_agent_does_not_commit_when_independent_verification_fails():
    files={"x.py":"old"}
    committed=[]
    agent=GitHubCodeAgent(read=lambda target: files[target],test=lambda: True,commit=lambda *a: committed.append(a) or "bad")
    plan=agent.prepare(target="x.py",proposed_content="new",description="verification required")
    result=agent.execute(plan,apply=lambda p: files.__setitem__(p.target,"new"),verify=lambda p: False)
    assert result.committed is False
    assert committed==[]
