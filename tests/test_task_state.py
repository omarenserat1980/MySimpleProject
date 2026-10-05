import pytest

from platform_foundation.task_state import InvalidTaskTransition, TaskStatus, transition


def test_normal_success_path() -> None:
    state = transition(TaskStatus.PENDING, TaskStatus.RUNNING)
    state = transition(state, TaskStatus.SUCCESS)
    assert state is TaskStatus.SUCCESS


def test_failure_can_retry() -> None:
    state = transition(TaskStatus.RUNNING, TaskStatus.FAILED)
    state = transition(state, TaskStatus.RETRYING)
    assert transition(state, TaskStatus.RUNNING) is TaskStatus.RUNNING


def test_success_cannot_be_reopened() -> None:
    with pytest.raises(InvalidTaskTransition):
        transition(TaskStatus.SUCCESS, TaskStatus.RUNNING)


def test_pending_cannot_jump_to_success() -> None:
    with pytest.raises(InvalidTaskTransition):
        transition(TaskStatus.PENDING, TaskStatus.SUCCESS)
