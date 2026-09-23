from brain_v7.braincore_v2.employee_hierarchy import EmployeeHierarchy


def test_initial_hierarchy_has_ten_employees():
    org = EmployeeHierarchy(initial_employees=10)
    snap = org.snapshot()
    assert snap["employee_count"] == 10
    assert snap["manager_count"] == 11
    assert snap["root_manager"] == "BRAIN-001"


def test_task_routes_employee_to_manager_to_brain():
    org = EmployeeHierarchy(initial_employees=10)
    task = org.assign_task("ابحث عن فرصة جديدة")
    assert task.status == "ASSIGNED"
    assert task.assigned_to is not None
    assert task.manager_id in {"MGR-001", "MGR-002"}
    assert task.escalation_path[-1] == "BRAIN-001"


def test_can_scale_to_one_hundred_employees():
    org = EmployeeHierarchy(initial_employees=10)
    org.add_employees(90)
    assert org.snapshot()["employee_count"] == 100


def test_completion_returns_employee_to_available():
    org = EmployeeHierarchy(initial_employees=1)
    task = org.assign_task("مهمة")
    org.complete_task(task.task_id, success=True)
    employee = org.employees[task.assigned_to]
    assert employee.status == "AVAILABLE"
    assert employee.completed_tasks == 1


def test_full_staffing_plan_has_64_workers_below_brain():
    org = EmployeeHierarchy()
    summary = org.staffing_summary()
    assert summary["departments"] == 11
    assert summary["department_managers"] == 11
    assert summary["specialist_employees"] == 53
    assert summary["total_ai_workers_below_brain"] == 64
