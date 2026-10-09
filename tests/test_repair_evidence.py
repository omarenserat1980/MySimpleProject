from platform_foundation.repair_evidence import RepairEvidence, evidence_is_complete
from platform_foundation.repair_executor import BoundedRepairExecutor
from platform_foundation.workflow_inspector import WorkflowInspector


def test_repair_evidence_captures_inspection_and_execution():
    inspection = WorkflowInspector().inspect(
        {"sha": "abc", "error": "runner timeout"},
        target_sha="abc",
    )
    result = BoundedRepairExecutor().execute(
        inspection.evidence,
        target_sha=inspection.target_sha,
        observed_sha=inspection.observed_sha,
        rerun=lambda: True,
        verify=lambda: True,
    )
    evidence = RepairEvidence.from_results(inspection, result)
    record = evidence.to_dict()
    assert evidence_is_complete(record)
    assert record["target_sha"] == "abc"
    assert record["failure_class"] == "EXECUTION_INFRA"
    assert record["repair_action"] == "RERUN"
    assert record["succeeded"] is True


def test_blocked_cross_sha_is_recorded_as_blocked():
    inspection = WorkflowInspector().inspect(
        {"sha": "old", "error": "runner timeout"},
        target_sha="new",
    )
    result = BoundedRepairExecutor().execute(
        inspection.evidence,
        target_sha=inspection.target_sha,
        observed_sha=inspection.observed_sha,
        rerun=lambda: True,
        verify=lambda: True,
    )
    record = RepairEvidence.from_results(inspection, result).to_dict()
    assert record["allowed"] is False
    assert record["attempted"] is False
    assert record["succeeded"] is False
    assert evidence_is_complete(record)
