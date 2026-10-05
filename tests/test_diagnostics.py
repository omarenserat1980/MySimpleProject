from platform_foundation.diagnostics import capture_exception


def test_capture_exception_is_structured() -> None:
    try:
        raise ValueError("bad-input")
    except ValueError as exc:
        evidence = capture_exception("task-1", exc)

    assert evidence.task_id == "task-1"
    assert evidence.error_type == "ValueError"
    assert evidence.error == "bad-input"
    assert "ValueError: bad-input" in evidence.traceback
    assert evidence.as_dict()["task_id"] == "task-1"
