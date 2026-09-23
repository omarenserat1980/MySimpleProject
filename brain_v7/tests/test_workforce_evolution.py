from brain_v7.braincore_v2.employee_hierarchy import EmployeeHierarchy
from brain_v7.braincore_v2.notifications import NotificationCenter
from brain_v7.braincore_v2.workforce_evolution import WorkforceEvolutionEngine


def test_evolution_can_create_dynamic_capacity():
    org = EmployeeHierarchy(initial_employees=1)
    notifications = NotificationCenter()
    engine = WorkforceEvolutionEngine(org, notifications, max_active_workers=10)
    before = len(org.employees)
    result = engine.evolve("إنتاج فيديو سينمائي")
    assert result["continuous_evolution"] is True
    assert len(org.employees) >= before
    assert notifications.snapshot()["count"] >= 1


def test_strong_employee_is_promoted():
    org = EmployeeHierarchy(initial_employees=1)
    employee = next(iter(org.employees.values()))
    employee.completed_tasks = 10
    employee.failed_tasks = 0
    notifications = NotificationCenter()
    result = WorkforceEvolutionEngine(org, notifications).evolve("مهمة")
    assert employee.employee_id in result["promoted"]
    assert employee.title.startswith("Senior ")


def test_weak_employee_is_retired():
    org = EmployeeHierarchy(initial_employees=1)
    employee = next(iter(org.employees.values()))
    employee.completed_tasks = 0
    employee.failed_tasks = 8
    notifications = NotificationCenter()
    result = WorkforceEvolutionEngine(org, notifications).evolve("مهمة")
    assert employee.employee_id in result["retired"]
    assert employee.status == "RETIRED"
