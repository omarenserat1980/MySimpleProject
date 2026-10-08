from __future__ import annotations

"""Single bridge from Mission Control to Execution Kernel and Resource Fabric.

Admission only. Actual side effects remain owned by workers after receiving the
fenced execution envelope and resource reservation.
"""

from typing import Any

from .mission_control import plan
from brain_v12.brain.execution_kernel import ExecutionKernel
from brain_v12.brain.resource_fabric import ResourceFabric, ResourceRequest


class MissionExecutionCoordinator:
    def __init__(self, fabric: ResourceFabric, kernel: ExecutionKernel) -> None:
        self.fabric = fabric
        self.kernel = kernel

    def admit(
        self,
        *,
        mission: str,
        owner: str,
        requests: list[ResourceRequest],
        evidence_confidence: float = 0.0,
        external_side_effects: bool = False,
        ttl_seconds: int | None = None,
    ) -> dict[str, Any]:
        mission_plan = plan(
            mission,
            evidence_confidence=evidence_confidence,
            external_side_effects=external_side_effects,
        )

        if mission_plan.requires_authorization:
            return {
                "ok": False,
                "status": "AUTHORIZATION_REQUIRED",
                "mission_fingerprint": mission_plan.mission_fingerprint,
                "decision_evidence": mission_plan.decision_evidence.canonical(),
            }

        intent_id = "mission:" + mission_plan.mission_fingerprint[:24]
        placement = self.fabric.plan(intent_id, requests)
        if not placement["ok"]:
            return {
                "ok": False,
                "status": "CAPACITY_BLOCKED",
                "intent_id": intent_id,
                "mission_fingerprint": mission_plan.mission_fingerprint,
                "placement": placement,
            }

        kernel_result = self.kernel.admit(
            intent_id=intent_id,
            operation="mission_execution",
            owner=owner,
            payload={
                "mission_fingerprint": mission_plan.mission_fingerprint,
                "resources": placement["allocations"],
            },
            capacity_admitted=True,
        )
        if not kernel_result["ok"]:
            return {
                "ok": False,
                "status": kernel_result["status"],
                "intent_id": intent_id,
                "kernel": kernel_result,
                "placement": placement,
            }

        reservation = self.fabric.reserve(
            intent_id,
            allocations=placement["allocations"],
            ttl_seconds=ttl_seconds,
        )
        if not reservation["ok"]:
            self.kernel.finish(
                kernel_result["envelope"]["execution_id"],
                kernel_result["envelope"]["epoch"],
                "RESERVATION_FAILED",
            )
            return {
                "ok": False,
                "status": "RESOURCE_RESERVATION_FAILED",
                "intent_id": intent_id,
                "kernel": kernel_result,
                "reservation": reservation,
            }

        return {
            "ok": True,
            "status": "ADMITTED",
            "intent_id": intent_id,
            "mission_fingerprint": mission_plan.mission_fingerprint,
            "execution": kernel_result["envelope"],
            "reservation": reservation["reservation"],
            "decision_evidence": mission_plan.decision_evidence.canonical(),
        }

    def finish(self, execution_id: str, epoch: int, reservation_id: str,
               status: str = "COMPLETED") -> dict[str, Any]:
        check = self.kernel.validate(execution_id, epoch)
        if not check["ok"]:
            return check
        released = self.fabric.release(reservation_id)
        if not released["ok"]:
            return {
                "ok": False,
                "status": "RESOURCE_RELEASE_FAILED",
                "release": released,
            }
        return self.kernel.finish(execution_id, epoch, status)
