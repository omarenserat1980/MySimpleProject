from brain_v7.braincore_v2.operations_dashboard import OperationsDashboard


def test_dashboard_is_auditable_and_bounded():
    d = OperationsDashboard()
    d.control.heartbeat("worker-1")
    job = d.jobs.create("research")
    snap = d.snapshot(brain={
        "cycle": 1, "objective": "research", "selected_internal_focus": "RESEARCH",
        "organization": {}, "external_work": {}, "external_work_metrics": {},
        "completion_report": {},
    })
    assert snap["brain_cycle"] == 1
    assert snap["control_plane"]["health"]["live_workers"] == 1
    assert snap["safety"]["money_movement"] is False
