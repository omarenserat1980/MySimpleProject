from brain_v12.self_healing.completion_audit import (
    is_intentional_not_implemented_state,
    main,
)


def test_completion_audit_runs():
    assert main() == 0


def test_explicit_blocked_mining_status_is_not_a_todo_marker():
    assert is_intentional_not_implemented_state(
        '"native_mining_backend": "NOT_IMPLEMENTED",'
    )
    assert is_intentional_not_implemented_state(
        '"stratum_pool_adapter": "NOT_IMPLEMENTED",'
    )


def test_unrelated_not_implemented_marker_is_still_reported():
    assert not is_intentional_not_implemented_state(
        'raise RuntimeError("TOOL_NOT_IMPLEMENTED_OR_APPROVED")'
    )
    assert not is_intentional_not_implemented_state(
        '"provider_adapter": "NOT_IMPLEMENTED",'
    )
