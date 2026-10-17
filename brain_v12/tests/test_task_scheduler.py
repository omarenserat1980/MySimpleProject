from brain_v12.brain.resource_fabric import ResourceRecord, ResourceState
from brain_v12.brain.task_scheduler import ScheduleStatus, TaskRequest, select_resource


def test_selects_smallest_fitting_available_resource_without_execution():
    resources = [
        ResourceRecord("large", "cloud", "test", ResourceState.AVAILABLE, 8, 8192, 100),
        ResourceRecord("small", "local", "test", ResourceState.AVAILABLE, 2, 2048, 20),
    ]
    result = select_resource(TaskRequest("task-1", 1, 512, 1), resources)
    assert result.status == ScheduleStatus.SELECTED
    assert result.resource_id == "small"
    assert result.reason == "POLICY_SELECTION_ONLY_NOT_EXECUTED"


def test_unknown_capacity_is_not_treated_as_available():
    resources = [ResourceRecord("unknown", "device", "test")]
    result = select_resource(TaskRequest("task-2"), resources)
    assert result.status == ScheduleStatus.NO_RESOURCE
    assert result.resource_id is None


def test_available_but_insufficient_resource_defers():
    resources = [ResourceRecord("tiny", "local", "test", ResourceState.AVAILABLE, 1, 128, 0)]
    result = select_resource(TaskRequest("task-3", 2, 1024, 1), resources)
    assert result.status == ScheduleStatus.DEFERRED


def test_invalid_task_requirements_are_rejected():
    try:
        TaskRequest("task-4", required_vcpu=0)
    except ValueError as exc:
        assert str(exc) == "TASK_RESOURCE_REQUIREMENTS_INVALID"
    else:
        raise AssertionError("invalid request accepted")
