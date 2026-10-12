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
    VIRTUAL_PHONE = "virtual_phone"
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
    """Return logical profiles, not claims that devices are currently online."""
    return (
        DeviceEndpoint(
            endpoint_id="arkan-virtual-01",
            display_name="Arkan virtual computer",
            role=EndpointRole.VIRTUAL_COMPUTER,
            platform="brain-simulator",
            allowed_workloads=(Workload.VIRTUAL_SIMULATION,),
            notes=(
                "Canonical software-defined identity. Simulator provisioning and a supported "
                "task must be verified before execution; never alias this identity to a physical host."
            ),
        ),
        DeviceEndpoint(
            endpoint_id="phone-virtual-01",
            display_name="هاتف برين الافتراضي",
            role=EndpointRole.VIRTUAL_PHONE,
            platform="brain-mobile-simulator",
            allowed_workloads=(Workload.VIRTUAL_SIMULATION,),
            notes=(
                "Software-only phone profile; not a physical Android handset and not a claim "
                "that Android OS or an emulator process is currently running."
            ),
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


def build_fleet_status(
    agent_status: dict,
    virtual_computer_status: dict | None = None,
    virtual_phone_status: dict | None = None,
) -> dict:
    """Join agent heartbeats with live evidence from the software Arkan simulator.

    Device heartbeats alone never verify identity. Arkan's eligibility is based
    only on its canonical persisted ID, an in-process simulator boot, and a
    passing bounded symbolic task; it grants simulation capability only.
    """
    agents = agent_status.get("agents", []) if isinstance(agent_status, dict) else []
    ttl = max(5, int(agent_status.get("ttl_seconds", 15))) if isinstance(agent_status, dict) else 15
    observed = {str(item.get("agent_id", "")): item for item in agents if isinstance(item, dict)}
    virtual_status = virtual_computer_status if isinstance(virtual_computer_status, dict) else {}
    phone_status = virtual_phone_status if isinstance(virtual_phone_status, dict) else {}
    arkan_identity_verified = (
        virtual_status.get("exists") is True
        and virtual_status.get("device_id") == "arkan-virtual-01"
        and virtual_status.get("identity_independent_of_host") is True
    )
    runtime_status = virtual_status.get("runtime_status", {})
    booted = (
        virtual_status.get("runtime_loaded") is True
        and virtual_status.get("simulator_booted") is True
        and isinstance(runtime_status, dict)
        and runtime_status.get("powered") is True
    )
    task_evidence = virtual_status.get("task_execution_evidence", {})
    task_passed = isinstance(task_evidence, dict) and task_evidence.get("status") == "PASS"
    arkan_ready = arkan_identity_verified and booted and task_passed

    phone_identity_verified = (
        phone_status.get("exists") is True
        and phone_status.get("device_id") == "phone-virtual-01"
        and phone_status.get("identity_independent_of_host") is True
    )
    phone_runtime = phone_status.get("runtime_status", {})
    phone_booted = (
        phone_status.get("runtime_loaded") is True
        and phone_status.get("simulator_booted") is True
        and isinstance(phone_runtime, dict)
        and phone_runtime.get("powered") is True
    )
    phone_evidence = phone_status.get("task_execution_evidence", {})
    phone_task_passed = (
        isinstance(phone_evidence, dict) and phone_evidence.get("status") == "PASS"
    )
    phone_ready = phone_identity_verified and phone_booted and phone_task_passed

    rows = []
    for endpoint in default_fleet():
        if endpoint.endpoint_id == "arkan-virtual-01":
            if arkan_ready:
                observed_state = "SIMULATION_READY"
            elif virtual_status.get("exists") is True:
                observed_state = "CONFIGURED_NOT_RUNNING" if not booted else "DEGRADED"
            else:
                observed_state = "NOT_PROVISIONED"
            rows.append({
                **endpoint.public(),
                "indicator_selected": True,
                "reality": "SIMULATED",
                "physical_device_required": False,
                "observed_state": observed_state,
                "heartbeat_age_seconds": None,
                "heartbeat_ttl_seconds": None,
                "identity_verified": arkan_identity_verified,
                "execution_eligible": arkan_ready,
                "readiness": "SIMULATION_READY" if arkan_ready else observed_state,
                "native_os_boot_verified": False,
                "supported_execution": ["bounded_symbolic_virtual_simulation"] if arkan_ready else [],
            })
            continue

        if endpoint.endpoint_id == "phone-virtual-01":
            if phone_ready:
                observed_state = "SIMULATION_READY"
            elif phone_status.get("exists") is True:
                observed_state = "CONFIGURED_NOT_RUNNING" if not phone_booted else "DEGRADED"
            else:
                observed_state = "PROFILE_REGISTERED_NOT_RUNNING"
            rows.append({
                **endpoint.public(),
                "indicator_selected": False,
                "reality": "SIMULATED",
                "physical_device_required": False,
                "observed_state": observed_state,
                "heartbeat_age_seconds": None,
                "heartbeat_ttl_seconds": None,
                "identity_verified": phone_identity_verified,
                "execution_eligible": phone_ready,
                "readiness": "SIMULATION_READY" if phone_ready else observed_state,
                "native_os_boot_verified": False,
                "supported_execution": ["bounded_mobile_simulation"] if phone_ready else [],
            })
            continue

        heartbeat = observed.get(endpoint.endpoint_id)
        age = heartbeat.get("age_seconds") if heartbeat else None
        is_online = bool(heartbeat and heartbeat.get("online") and age is not None and float(age) <= ttl)
        rows.append({
            **endpoint.public(),
            "indicator_selected": False,
            "reality": "OBSERVED_DEVICE" if is_online else "UNKNOWN",
            "physical_device_required": endpoint.role == EndpointRole.ANDROID_AGENT,
            "observed_state": "ONLINE" if is_online else ("STALE" if heartbeat else "NOT_OBSERVED"),
            "heartbeat_age_seconds": age,
            "heartbeat_ttl_seconds": ttl,
            "identity_verified": False,
            "execution_eligible": False,
        })
    selected_arkan = next(row for row in rows if row["endpoint_id"] == "arkan-virtual-01")
    return {
        "ok": True,
        "status": "OBSERVED_NOT_EXECUTION_READY",
        "source": "device_bridge.agent_status+software_virtual_nodes",
        "active_software_node": {
            "endpoint_id": "arkan-virtual-01",
            "display_name": "Arkan virtual computer",
            "indicator_target": "arkan-virtual-01",
            "indicator_state": selected_arkan["observed_state"],
            "reality": "SIMULATED",
            "physical_device_required": False,
            "execution_eligible": selected_arkan["execution_eligible"],
            "note": "Selected as the software-only Arkan computer profile; selection does not prove a running native OS.",
        },
        "virtual_tool_indicators": [
            {
                "tool": "termux_emulator",
                "display_name": "BRAIN Termux Virtual Runtime",
                "indicator_target": "brain-termux-virtual-01",
                "owner": "Electronic Brain",
                "execution_mode": "BRAIN_MANAGED_VIRTUAL",
                "reality": "SIMULATED",
                "physical_device_required": False,
                "external_app_required": False,
                "observed_state": "CONFIGURED_NOT_PROVEN",
                "execution_eligible": False,
                "note": "Logical Brain runtime target only; do not route to redmi3-01 or any installed Termux app without explicit, fresh authorization.",
            },
            {
                "tool": "powershell_emulator",
                "display_name": "BRAIN PowerShell Emulator",
                "indicator_target": "arkan-virtual-01",
                "owner": "Electronic Brain",
                "execution_mode": "BRAIN_MANAGED_EMULATOR",
                "reality": "SIMULATED",
                "physical_device_required": False,
                "external_app_required": False,
                "observed_state": "SIMULATION_READY" if selected_arkan["execution_eligible"] else selected_arkan["observed_state"],
                "execution_eligible": selected_arkan["execution_eligible"],
                "note": "Uses Brain's sandboxed PowerShell-like interpreter; it does not launch Windows PowerShell or prove Windows Server boot.",
            },
            {
                "tool": "desktop_commander_emulator",
                "display_name": "BRAIN Desktop Commander Emulator",
                "indicator_target": "arkan-virtual-01",
                "owner": "Electronic Brain",
                "execution_mode": "BRAIN_MANAGED_EMULATOR",
                "reality": "SIMULATED",
                "physical_device_required": False,
                "external_app_required": False,
                "observed_state": "SIMULATION_READY" if selected_arkan["execution_eligible"] else selected_arkan["observed_state"],
                "execution_eligible": selected_arkan["execution_eligible"],
                "note": "Uses Brain's sandboxed virtual filesystem/process model; it does not connect to the physical Desktop Commander agent.",
            },
        ],
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
