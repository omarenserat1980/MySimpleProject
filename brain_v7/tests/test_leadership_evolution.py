from brain_v7.braincore_v2.employee_hierarchy import EmployeeHierarchy
from brain_v7.braincore_v2.notifications import NotificationCenter
from brain_v7.braincore_v2.leadership_evolution import LeadershipEvolutionEngine


def test_leaderboard_is_competitive():
    org = EmployeeHierarchy(initial_employees=2)
    employees = list(org.employees.values())
    employees[0].completed_tasks = 20
    employees[0].failed_tasks = 0
    employees[1].completed_tasks = 12
    employees[1].failed_tasks = 4
    engine = LeadershipEvolutionEngine(org, NotificationCenter())
    result = engine.evaluate()
    assert result["leaderboard"][0]["employee_id"] == employees[0].employee_id


def test_strong_employee_can_succeed_brain():
    org = EmployeeHierarchy(initial_employees=2)
    employee = list(org.employees.values())[0]
    employee.completed_tasks = 30
    employee.failed_tasks = 0
    notifications = NotificationCenter()
    engine = LeadershipEvolutionEngine(org, notifications)
    result = engine.run()
    assert result["succession_performed"] is True
    assert result["successor_id"] == employee.employee_id
    assert engine.record.active_brain_id == employee.employee_id
    assert employee.status == "BRAIN_SUCCESSOR"
