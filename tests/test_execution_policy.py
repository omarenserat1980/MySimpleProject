from platform_foundation.execution_policy import (
    BrainExecutionPolicy, ExecutionMode, ExecutorDecision, ExecutorDescriptor,
)


def brain(executor_id="brain-runner-01", caps=frozenset({"python", "ffmpeg"})):
    return ExecutorDescriptor(executor_id, "brain", True, caps)


def external(executor_id="github-hosted", caps=frozenset({"python", "ffmpeg"})):
    return ExecutorDescriptor(executor_id, "github", False, caps)


def test_brain_executor_is_selected_first():
    result = BrainExecutionPolicy().select([external(), brain()])
    assert result.decision is ExecutorDecision.ALLOWED
    assert result.executor_id == "brain-runner-01"


def test_external_runner_is_blocked_by_default():
    result = BrainExecutionPolicy().select([external()])
    assert result.decision is ExecutorDecision.BLOCKED
    assert result.executor_id is None
    assert "fallback forbidden" in result.reason


def test_external_mode_requires_explicit_policy():
    result = BrainExecutionPolicy(ExecutionMode.EXTERNAL_ALLOWED).select([external()])
    assert result.decision is ExecutorDecision.ALLOWED
    assert result.executor_id == "github-hosted"


def test_capability_mismatch_blocks_even_when_brain_exists():
    result = BrainExecutionPolicy().select(
        [brain(caps=frozenset({"python"})), external()],
        required_capabilities={"ffmpeg"},
    )
    assert result.decision is ExecutorDecision.BLOCKED


def test_brain_must_be_persistent():
    transient = ExecutorDescriptor("brain-transient", "brain", False, frozenset({"python"}))
    result = BrainExecutionPolicy().select([transient])
    assert result.decision is ExecutorDecision.BLOCKED
