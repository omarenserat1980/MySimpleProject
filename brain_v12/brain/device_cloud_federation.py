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
    ANDROID_AGENT = "android_agent"
    VEHICLE_CLIENT = "vehicle_client"


class Workload(str, Enum):
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
    """Return logical profiles, not claims that devices are currently online."""
    return (
        DeviceEndpoint(
            endpoint_id="arkan",
            display_name="Arkan Windows host",
            role=EndpointRole.COMPUTE_HOST,
            platform="windows",
            allowed_workloads=(Workload.BUILD_TEST, Workload.MEDIA_RENDER,
                               Workload.SYNC_BACKUP),
            notes="Host identity, available RAM, and VM boot must be verified live.",
        ),
        DeviceEndpoint(
            endpoint_id="redmi3-01",
            display_name="Redmi Android agent",
            role=EndpointRole.ANDROID_AGENT,
            platform="android-termux",
            allowed_workloads=(Workload.SYNC_BACKUP,),
            notes="Android missions require fresh authenticated agent evidence.",
        ),
        DeviceEndpoint(
            endpoint_id="realme-pending-identity",
            display_name="Realme Android endpoint (identity pending)",
            role=EndpointRole.ANDROID_AGENT,
            platform="android",
            allowed_workloads=(Workload.SYNC_BACKUP,),
            notes="Placeholder only; bind the actual agent ID and model after discovery.",
        ),
        DeviceEndpoint(
            endpoint_id="honda-enp1-2023",
            display_name="Honda e:NP1 2023 / Honda CONNECT",
            role=EndpointRole.VEHICLE_CLIENT,
            platform="vehicle-infotainment",
            allowed_workloads=(Workload.CAR_COMPANION, Workload.SYNC_BACKUP),
            notes="Companion/information only; never route vehicle control or safety functions.",
        ),
    )


def build_fleet_status(agent_status: dict) -> dict:
    """Join logical fleet profiles to observed Agent Gateway heartbeats.

    A heartbeat is liveness evidence, not a unique device identity proof.
    Consequently this read-only view never marks an endpoint identity-verified
    or eligible for execution. Cloud capacity and free entitlement are likewise
    left unverified until provider-specific evidence is supplied.
    """
    agents = agent_status.get("agents", []) if isinstance(agent_status, dict) else []
    ttl = max(5, int(agent_status.get("ttl_seconds", 15))) if isinstance(agent_status, dict) else 15
    observed = {str(item.get("agent_id", "")): item for item in agents if isinstance(item, dict)}
    rows = []
    for endpoint in default_fleet():
        heartbeat = observed.get(endpoint.endpoint_id)
        age = heartbeat.get("age_seconds") if heartbeat else None
        is_online = bool(heartbeat and heartbeat.get("online") and age is not None and float(age) <= ttl)
        rows.append({
            **endpoint.public(),
            "observed_state": "ONLINE" if is_online else ("STALE" if heartbeat else "NOT_OBSERVED"),
            "heartbeat_age_seconds": age,
            "heartbeat_ttl_seconds": ttl,
            "identity_verified": False,
            "execution_eligible": False,
        })
    return {
        "ok": True,
        "status": "OBSERVED_NOT_EXECUTION_READY",
        "source": "device_bridge.agent_status",
        "fleet": rows,
        "cloud": {
            "status": "NOT_PROBED",
            "capacity_verified": False,
            "free_cost_gate_passed": False,
            "paid_provisioning_allowed": False,
        },
        "notes": [
            "Heartbeat proves recent contact only, not unique hardware identity.",
            "No cloud resources are created by this status endpoint.",
            "Honda is an information/companion endpoint, not a compute executor.",
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
