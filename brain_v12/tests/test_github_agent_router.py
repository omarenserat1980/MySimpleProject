from brain_v12.github_agent_router import GitHubAgentRouter

def test_routes():
    r=GitHubAgentRouter()
    assert r.plan('pull request').domain=='pull-requests'
    assert r.plan('actions').action=='actions_runs'
    assert r.plan('code_write').requires_approval is True
