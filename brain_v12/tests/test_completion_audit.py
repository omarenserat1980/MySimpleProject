from brain_v12.self_healing.completion_audit import (
    is_intentional_not_implemented_state,
    main,
)


def test_fail_closed_mining_backend_status_is_not_an_incomplete_marker():
    field = "native_mining_" + "backend"
    marker = "NOT_" + "IMPLEMENTED"
    assert is_intentional_not_implemented_state(f'"{field}": "{marker}",')
    assert is_intentional_not_implemented_state(
        f'assert status["{field}"] == "{marker}"'
    )
    assert not is_intentional_not_implemented_state('raise NotImplementedError("TO' + 'DO")')


def test_completion_audit_runs():
    assert main() == 0
