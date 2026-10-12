from brain_v12.self_healing.emergency_resource_guard import EmergencyResourceGuard

def test_guard_starts_open():
    assert EmergencyResourceGuard().allow_new_work() is True

def test_recovery_reopens_guard():
    g=EmergencyResourceGuard()
    g.emergency=True
    g.breaches=3
    g.reset_after_recovery()
    assert g.allow_new_work() is True
