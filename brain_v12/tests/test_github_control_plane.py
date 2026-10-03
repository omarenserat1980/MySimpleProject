from brain_v12.github_control_plane import GitHubControlPlane, GitHubControlError

def test_catalog():
    d=GitHubControlPlane(token='test').capability_catalog()
    assert 'pull-requests' in d['domains'] and 'security' in d['domains']

def test_write_gate():
    try: GitHubControlPlane(token='test').authorize('code.write')
    except GitHubControlError as e: assert 'EXPLICIT_APPROVAL_REQUIRED' in str(e)
    else: raise AssertionError('write was not gated')

def test_blocked():
    try: GitHubControlPlane(token='test').authorize('financial.transfer')
    except GitHubControlError as e: assert 'BLOCKED_CAPABILITY' in str(e)
    else: raise AssertionError('blocked capability was authorized')


def test_workflow_dispatch_is_write_gated():
    cp=GitHubControlPlane(token="test")
    try:
        cp.dispatch_workflow("owner","repo","workflow.yml",ref="main")
    except GitHubControlError as e:
        assert "EXPLICIT_APPROVAL_REQUIRED:actions.write" in str(e)
    else:
        raise AssertionError("workflow dispatch bypassed approval")
