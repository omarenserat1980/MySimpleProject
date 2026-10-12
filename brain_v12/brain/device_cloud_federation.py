"""Safe cloud-offload policy for Brain's device fleet.

This module describes device roles and chooses an execution *plan* only.
It does not connect to devices, execute commands, provision cloud resources,
or control vehicle systems. Runtime liveness and identity must be supplied by
fresh, independently verified evidence.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Iterable


class EndpointRole(str, Enum):
    COMPUTE_HOST = "compute_host"
    VIRTUAL_COMPUTER = "virtual_computer"
    ANDROID_AGENT = "android_agent"
    VEHICLE_CLIENT = "vehicle_client"


class Workload(str, Enum):
    VIRTUAL_SIMULATION = "virtual_simulation"
    AI_INFERENCE = "ai_inference"
    BUILD_TEST = "build_test"
    MEDIA_RENDER = "media_render"
    SYNC_BACKUP = "sync_backup"
    CAR_COMPANION = "car_companion"


@dataclass(frozen=True)
class DeviceEndpoint:
    endpoint_id: str
    display_name: str
    role: EndpointRole
    platform: str
    identity_verified: bool = False
    online: bool = False
    allowed_workloads: tuple[Workload, ...] = ()
    notes: str = ""

    def public(self) -> dict:
        value = asdict(self)
        value["role"] = self.role.value
        value["allowed_workloads"] = [w.value for w in self.allowed_workloads]
        return value


@dataclass(frozen=True)
class ExecutionPlan:
    status: str
    target: str | None
    workload: str
    reasons: tuple[str, ...]

    def public(self) -> dict:
        return {
            "status": self.status,
            "target": self.target,
            "workload": self.workload,
            "reasons": list(self.reasons),
        }


def default_fleet() -> tuple[DeviceEndpoint, ...]:
    """Return software-node profiles only; profiles are not proof of liveness."""
    return (
        DeviceEndpoint(
            endpoint_id="brain-control-plane-main",
            display_name="Brain Control Plane API",
            role=EndpointRole.COMPUTE_HOST,
            platform="render-fastapi",
            allowed_workloads=(Workload.AI_INFERENCE, Workload.BUILD_TEST),
            notes="Serving this request proves API responsiveness only, not worker execution.",
        ),
        DeviceEndpoint(
            endpoint_id="arkan-software-executor",
            display_name="Arkan Software Executor",
            role=EndpointRole.VIRTUAL_COMPUTER,
            platform="python-software-worker",
            allowed_workloads=(Workload.VIRTUAL_SIMULATION, Workload.BUILD_TEST),
            notes="Software-only worker; require authenticated status and actual task-result evidence.",
        ),
        DeviceEndpoint(
            endpoint_id="github-actions-runner",
            display_name="GitHub Actions Hosted Runner",
            role=EndpointRole.COMPUTE_HOST,
            platform="github-hosted-runner",
            allowed_workloads=(Workload.BUILD_TEST,),
            notes="Ephemeral software runner; require a fresh workflow-run result.",
        ),
    )


def build_fleet_status(
    agent_status: dict | None = None,
    virtual_computer_status: dict | None = None,
) -> dict:
    """Report software-node indicators only; legacy hardware inputs are ignored."""
    rows = []
    for endpoint in default_fleet():
        if endpoint.endpoint_id == "brain-control-plane-main":
            state, evidence = "SERVING_STATUS_REQUEST", "current_http_request"
        elif endpoint.endpoint_id == "arkan-software-executor":
            state, evidence = "NOT_PROBED", "authenticated_executor_status_required"
        else:
            state, evidence = "NO_FRESH_RUN_EVIDENCE", "github_workflow_run_required"
        rows.append({
            **endpoint.public(),
            "observed_state": state,
            "readiness": state,
            "status_evidence": evidence,
            "heartbeat_age_seconds": None,
            "heartbeat_ttl_seconds": None,
            "identity_verified": endpoint.endpoint_id == "brain-control-plane-main",
            "execution_eligible": False,
        })
    return {
        "ok": True,
        "mode": "software-only",
        "status": "SOFTWARE_NODES_ONLY",
        "source": "software_node_status",
        "hardware_indicators_enabled": False,
        "hardware_nodes": [],
        "fleet": rows,
        "cloud": {
            "status": "NOT_PROBED",
            "capacity_verified": False,
            "free_cost_gate_passed": False,
            "paid_provisioning_allowed": False,
        },
        "notes": [
            "Physical hardware, Android, Termux, vehicle and host indicators are excluded.",
            "A software-node profile is not proof of a running worker.",
            "Execution eligibility remains false until an actual task result is independently verified.",
        ],
    }


def plan_execution(
    workload: Workload,
    endpoints: Iterable[DeviceEndpoint] | None = None,
    *,
    cloud_capacity_verified: bool = False,
    free_cost_gate_passed: bool = False,
) -> ExecutionPlan:
    """Select a verified local endpoint or a verified free cloud executor.

    A cloud route requires both fresh capacity evidence and a passed free-cost
    gate. The Honda endpoint is never an execution target for compute workloads.
    This is a planning contract; it does not perform the selected work.
    """
    endpoints = tuple(default_fleet() if endpoints is None else endpoints)

    for endpoint in endpoints:
        if endpoint.role == EndpointRole.VEHICLE_CLIENT and workload != Workload.CAR_COMPANION:
            continue
        if workload not in endpoint.allowed_workloads:
            continue
        if not endpoint.identity_verified:
            continue
        if not endpoint.online:
            continue
        return ExecutionPlan(
            status="LOCAL_TARGET_VERIFIED",
            target=endpoint.endpoint_id,
            workload=workload.value,
            reasons=("identity_verified", "fresh_online_evidence", "workload_allowed"),
        )

    if cloud_capacity_verified and free_cost_gate_passed:
        return ExecutionPlan(
            status="CLOUD_TARGET_VERIFIED",
            target="brain-cloud-free-pool",
            workload=workload.value,
            reasons=("cloud_capacity_verified", "free_cost_gate_passed"),
        )

    return ExecutionPlan(
        status="BLOCKED_NO_VERIFIED_EXECUTOR",
        target=None,
        workload=workload.value,
        reasons=(
            "no_online_identity_verified_endpoint",
            "cloud_fallback_requires_verified_capacity_and_free_cost_gate",
        ),
    )
