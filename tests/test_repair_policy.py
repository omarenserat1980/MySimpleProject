from platform_foundation.repair_policy import (
    FailureClass,
    RepairAction,
    RepairPolicy,
)


def test_classifies_and_allows_bounded_infrastructure_rerun():
    policy = RepairPolicy()
    scope = policy.admit(
        "runner timeout while queued",
        target_sha="abc",
        observed_sha="abc",
    )
    assert scope.failure_class is FailureClass.EXECUTION_INFRA
    assert scope.action is RepairAction.RERUN
    assert scope.allowed is True


def test_artifact_failure_allows_rebuild_not_code_patch():
    scope = RepairPolicy().scope("artifact missing: final.mp4")
    assert scope.failure_class is FailureClass.ARTIFACT
    assert scope.action is RepairAction.REBUILD_ARTIFACT
    assert scope.allowed is True


def test_dependency_is_blocked_for_review():
    scope = RepairPolicy().scope("ModuleNotFoundError: missing package")
    assert scope.failure_class is FailureClass.DEPENDENCY
    assert scope.action is RepairAction.BLOCK_FOR_REVIEW
    assert scope.allowed is False


def test_unknown_is_blocked():
    scope = RepairPolicy().scope("unexpected failure")
    assert scope.failure_class is FailureClass.UNKNOWN
    assert scope.allowed is False


def test_cross_sha_repair_is_blocked():
    scope = RepairPolicy().admit(
        "runner timeout",
        target_sha="abc",
        observed_sha="def",
    )
    assert scope.allowed is False
    assert scope.action is RepairAction.BLOCK_FOR_REVIEW


def test_evidence_is_serializable():
    evidence = RepairPolicy().evidence(RepairPolicy().scope("runner timeout"))
    assert evidence["failure_class"] == "EXECUTION_INFRA"
    assert evidence["repair_action"] == "RERUN"
