from platform_foundation.repair_policy import FailureClass, RepairAction
from platform_foundation.workflow_inspector import WorkflowInspector


def test_inspector_extracts_sha_and_failure_evidence():
    result = WorkflowInspector().inspect(
        {"head_sha": "abc", "error": "runner timeout"},
        target_sha="abc",
    )
    assert result.observed_sha == "abc"
    assert result.failure_class is FailureClass.EXECUTION_INFRA
    assert result.scope.action is RepairAction.RERUN
    assert result.scope.allowed is True


def test_inspector_blocks_cross_commit_evidence():
    result = WorkflowInspector().inspect(
        {"sha": "old", "error": "runner timeout"},
        target_sha="new",
    )
    assert result.scope.allowed is False
    assert result.scope.action is RepairAction.BLOCK_FOR_REVIEW


def test_inspector_blocks_missing_sha():
    result = WorkflowInspector().inspect(
        {"error": "runner timeout"},
        target_sha="abc",
    )
    assert result.scope.allowed is False


def test_inspector_prefers_explicit_error_over_other_fields():
    result = WorkflowInspector().inspect(
        {"sha": "abc", "error": "artifact missing", "logs": "runner timeout"},
        target_sha="abc",
    )
    assert result.failure_class is FailureClass.ARTIFACT
