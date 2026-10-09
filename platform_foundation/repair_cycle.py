from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping

from .repair_evidence import RepairEvidence
from .repair_executor import BoundedRepairExecutor, RepairResult
from .workflow_inspector import InspectionResult, WorkflowInspector


@dataclass(frozen=True)
class RepairCycleResult:
    inspection: InspectionResult
    repair: RepairResult
    evidence: RepairEvidence

    @property
    def succeeded(self) -> bool:
        return self.repair.succeeded


class BoundedRepairCycle:
    """Run inspect -> repair -> independent verify -> structured evidence."""

    def __init__(
        self,
        inspector: WorkflowInspector | None = None,
        executor: BoundedRepairExecutor | None = None,
    ) -> None:
        self.inspector = inspector or WorkflowInspector()
        self.executor = executor or BoundedRepairExecutor()

    def run(
        self,
        record: Mapping[str, object],
        *,
        target_sha: str,
        rerun: Callable[[], bool] | None = None,
        rebuild_artifact: Callable[[], bool] | None = None,
        verify: Callable[[], bool] | None = None,
    ) -> RepairCycleResult:
        inspection = self.inspector.inspect(record, target_sha=target_sha)
        repair = self.executor.execute(
            inspection.evidence,
            target_sha=inspection.target_sha,
            observed_sha=inspection.observed_sha,
            rerun=rerun,
            rebuild_artifact=rebuild_artifact,
            verify=verify,
        )
        evidence = RepairEvidence.from_results(inspection, repair)
        return RepairCycleResult(inspection, repair, evidence)


__all__ = ["BoundedRepairCycle", "RepairCycleResult"]
