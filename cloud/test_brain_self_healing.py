from cloud.brain_self_healing import _actions_for, ALLOWLIST
from cloud.brain_interview import conduct_interview

def test_interview_drives_allowlisted_actions():
    report = conduct_interview()
    actions = _actions_for(report)
    keys = [a.key for a in actions]
    assert "interview_tests" in keys
    assert all(key in ALLOWLIST for key in keys)

def test_no_arbitrary_commands():
    assert all(isinstance(a.command, tuple) for a in ALLOWLIST.values())
    assert all(a.command[0] for a in ALLOWLIST.values())
