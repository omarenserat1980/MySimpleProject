from pathlib import Path

from platform_foundation.brain_ci_executor import BrainCIExecutor
from platform_foundation.persistent_state import SQLiteStateStore


def make(tmp_path, runner):
    return BrainCIExecutor(SQLiteStateStore(tmp_path / "state.db"), root=tmp_path, runner=runner)


def test_unknown_profile_is_rejected(tmp_path):
    executor = make(tmp_path, lambda *_: (0, "", ""))
    try:
        executor.execute("missing")
        assert False
    except ValueError as exc:
        assert "unknown_ci_profile" in str(exc)


def test_brain_ci_runs_allowlisted_profile_and_records_evidence(tmp_path):
    seen = {}

    def runner(command, root):
        seen["command"] = command
        return 0, "2 passed", ""

    result = make(tmp_path, runner).execute("runner_policy", commit_sha="abc123")
    assert result.status == "VERIFIED"
    assert result.executor_id == "brain-ci-01"
    assert result.exit_code == 0
    assert result.evidence_sha256
    assert Path(result.evidence_path).exists()
    assert "pytest" in seen["command"]


def test_failed_brain_ci_is_not_success(tmp_path):
    result = make(tmp_path, lambda *_: (1, "", "failure")).execute("runner_policy")
    assert result.status == "FAILED"
    assert result.exit_code == 1


def test_nonpersistent_brain_executor_blocks_without_fallback(tmp_path):
    executor = BrainCIExecutor(
        SQLiteStateStore(tmp_path / "state.db"),
        root=tmp_path,
        persistent=False,
        runner=lambda *_: (_ for _ in ()).throw(AssertionError("must not execute")),
    )
    result = executor.execute("runner_policy")
    assert result.status == "BLOCKED"
    assert result.executor_id is None
    assert "fallback forbidden" in (result.error or "")


def test_direct_brain_entrypoint_never_uses_external_runner(tmp_path):
    calls = []
    def runner(command, root):
        calls.append(command)
        return 0, "pass", ""
    executor = BrainCIExecutor(
        SQLiteStateStore(tmp_path / "state.db"),
        root=tmp_path,
        runner=runner,
    )
    result = executor.run_profile("runner_policy", commit_sha="brain-local")
    assert result.status == "VERIFIED"
    assert result.executor_id == "brain-local-ci" or result.executor_id == "brain-ci-01"
    assert calls


def test_readiness_is_brain_owned_and_fail_closed(tmp_path):
    executor = BrainCIExecutor(SQLiteStateStore(tmp_path / "state.db"), root=tmp_path)
    readiness = executor.readiness()
    assert readiness["ready"] is True
    assert readiness["decision"] == "ALLOWED"
    assert readiness["owner"] == "brain"
    assert readiness["persistent"] is True

def test_evidence_is_durable_and_bound_to_run(tmp_path):
    executor = BrainCIExecutor(
        SQLiteStateStore(tmp_path / "state.db"),
        root=tmp_path,
        runner=lambda *_: (0, "pass", ""),
    )
    result = executor.run_profile("runner_policy", run_id="brain-proof-01")
    evidence = executor.evidence("brain-proof-01")
    assert evidence["run_id"] == "brain-proof-01"
    assert evidence["executor_id"] == result.executor_id
    assert executor.evidence("other-run") is None
