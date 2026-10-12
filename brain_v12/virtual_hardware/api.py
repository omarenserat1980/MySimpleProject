from __future__ import annotations

from threading import RLock
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request

from ..brain.control_auth import require_control_key
from .computer import VirtualComputer
from .arkan_provisioner import ARKAN_ID, arkan_status, provision_arkan
from .cpu_profiles import list_cpu_profiles
from .storage_profiles import list_storage_profiles
from .memory_profiles import list_memory_profiles
from .peripheral_profiles import GPU_PROFILES, NIC_PROFILES, MOTHERBOARD_PROFILES
from .server_fabric import (admit_server_workload, discover_backends, get_server_profile,
                            list_server_profiles, observe_host_capacity)


router = APIRouter(prefix="/api/virtual-hardware", tags=["virtual-hardware"])
_machines: dict[str, VirtualComputer] = {}
_lock = RLock()

_MACHINE_FIELDS = {
    "ram_size", "storage_size", "gpu_width", "gpu_height", "cpu_profile_id",
    "storage_profile_id", "ram_profile_id", "cache_enabled", "memory_channels",
    "memory_channel_width_bits", "configured_cas_latency_cycles", "gpu_profile_id",
    "nic_profile_id", "motherboard_profile_id", "external_network_enabled",
}


def _authorized(request: Request) -> None:
    require_control_key(request)


def _machine_or_404(machine_id: str) -> VirtualComputer:
    machine = _machines.get(machine_id)
    if machine is None:
        raise HTTPException(status_code=404, detail="VIRTUAL_MACHINE_NOT_FOUND")
    return machine


@router.get("/profiles")
def list_hardware_profiles():
    """Read-only reference profile catalog. No device or host resources are allocated."""
    return {
        "ok": True,
        "cpu": list_cpu_profiles(),
        "storage": list_storage_profiles(),
        "memory": list_memory_profiles(),
        "gpu": [profile.describe() for profile in GPU_PROFILES.values()],
        "network": [profile.describe() for profile in NIC_PROFILES.values()],
        "motherboard": [profile.describe() for profile in MOTHERBOARD_PROFILES.values()],
        "fidelity_contract": {
            "physical_performance_claim": False,
            "simulated_capacity_is_host_capacity": False,
            "cycle_accurate_models": [],
        },
    }


@router.post("/machines")
def create_virtual_machine(request: Request, body: dict):
    _authorized(request)
    machine_id = str(body.get("machine_id") or body.get("name") or f"brain-vm-{uuid4().hex[:12]}")
    settings = {key: body[key] for key in _MACHINE_FIELDS if key in body}
    try:
        machine = VirtualComputer(name=machine_id, **settings)
        validation = machine.validate_configuration()
        if not validation["ok"]:
            raise HTTPException(status_code=422, detail={"code": "MACHINE_MANIFEST_INVALID", "validation": validation})
    except HTTPException:
        raise
    except (ValueError, RuntimeError, TypeError) as exc:
        raise HTTPException(status_code=422, detail={"code": "MACHINE_CONFIGURATION_REJECTED", "error": str(exc)}) from exc
    with _lock:
        if machine_id in _machines:
            raise HTTPException(status_code=409, detail="VIRTUAL_MACHINE_ALREADY_EXISTS")
        _machines[machine_id] = machine
    return {"ok": True, "machine_id": machine_id, "validation": validation,
            "manifest": machine.hardware_manifest(), "status": machine.status(),
            "registry_durability": "process-local; use checkpoint endpoint for explicit recovery data"}


@router.get("/machines")
def list_virtual_machines(request: Request):
    _authorized(request)
    with _lock:
        return {"ok": True, "machines": [{"machine_id": key, "status": machine.status()}
                                         for key, machine in sorted(_machines.items())]}


@router.post("/arkan/provision")
def provision_canonical_arkan(request: Request):
    """Idempotently provision Arkan's software simulator and persist its identity."""
    _authorized(request)
    with _lock:
        existing = _machines.get(ARKAN_ID)
        try:
            result = provision_arkan(machine=existing)
        except (ValueError, RuntimeError, TypeError, OSError) as exc:
            raise HTTPException(status_code=409, detail={
                "code": "ARKAN_PROVISIONING_FAILED", "error": str(exc)
            }) from exc
        _machines[ARKAN_ID] = result["machine"]
    return {
        "ok": True,
        "record": result["record"],
        "runtime_loaded": True,
        "readiness": "SIMULATION_READY",
        "native_os_boot_verified": False,
    }


def read_arkan_runtime_status():
    """Return canonical identity plus live in-process simulator evidence."""
    with _lock:
        machine = _machines.get(ARKAN_ID)
        persisted = arkan_status()
        persisted["runtime_loaded"] = machine is not None
        if machine is not None:
            persisted["runtime_status"] = machine.status()
            persisted["simulator_booted"] = bool(
                machine.powered
                and machine.boot_record
                and machine.boot_record.get("ok")
            )
        else:
            persisted["simulator_booted"] = False
        return persisted


@router.get("/arkan/status")
def get_canonical_arkan_status(request: Request):
    """Read persisted identity and distinguish it from an in-memory simulator."""
    _authorized(request)
    return read_arkan_runtime_status()


@router.get("/machines/{machine_id}/manifest")
def get_machine_manifest(machine_id: str, request: Request):
    _authorized(request)
    return _machine_or_404(machine_id).hardware_manifest()


@router.get("/machines/{machine_id}")
def get_machine_status(machine_id: str, request: Request):
    _authorized(request)
    return _machine_or_404(machine_id).status()


@router.post("/machines/{machine_id}/boot")
def boot_virtual_machine(machine_id: str, request: Request):
    _authorized(request)
    machine = _machine_or_404(machine_id)
    try:
        return {"ok": True, "machine_id": machine_id, "status": machine.power_on()}
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=409, detail={"code": "MACHINE_BOOT_REJECTED", "error": str(exc),
                                                     "status": machine.status()}) from exc


@router.post("/machines/{machine_id}/workloads")
def execute_virtual_workload(machine_id: str, request: Request, body: dict):
    _authorized(request)
    machine = _machine_or_404(machine_id)
    program = body.get("program")
    if not isinstance(program, list):
        raise HTTPException(status_code=422, detail="PROGRAM_MUST_BE_A_LIST_OF_SYMBOLIC_INSTRUCTIONS")
    try:
        return {"ok": True, "machine_id": machine_id,
                "result": machine.execute(program, int(body.get("max_cycles", 10000)))}
    except (ValueError, RuntimeError, IndexError, TypeError) as exc:
        raise HTTPException(status_code=422, detail={"code": "WORKLOAD_REJECTED", "error": str(exc)}) from exc


@router.post("/machines/{machine_id}/benchmark")
def benchmark_virtual_machine(machine_id: str, request: Request, body: dict):
    _authorized(request)
    machine = _machine_or_404(machine_id)
    program = body.get("program")
    if not isinstance(program, list):
        raise HTTPException(status_code=422, detail="PROGRAM_MUST_BE_A_LIST_OF_SYMBOLIC_INSTRUCTIONS")
    try:
        return machine.run_benchmark(program, int(body.get("max_cycles", 10000)))
    except (ValueError, RuntimeError, IndexError, TypeError) as exc:
        raise HTTPException(status_code=422, detail={"code": "BENCHMARK_REJECTED", "error": str(exc)}) from exc


@router.post("/machines/{machine_id}/thermal/advance")
def advance_machine_thermal(machine_id: str, request: Request, body: dict):
    _authorized(request)
    machine = _machine_or_404(machine_id)
    try:
        return machine.advance_thermal(float(body["load_fraction"]), float(body["dt_seconds"]),
                                       float(body["power_watts"]) if body.get("power_watts") is not None else None)
    except (KeyError, ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail={"code": "THERMAL_UPDATE_REJECTED", "error": str(exc)}) from exc


@router.post("/machines/{machine_id}/checkpoint")
def checkpoint_virtual_machine(machine_id: str, request: Request):
    _authorized(request)
    return {"ok": True, "checkpoint": _machine_or_404(machine_id).checkpoint()}


@router.post("/machines/{machine_id}/restore")
def restore_virtual_machine(machine_id: str, request: Request, body: dict):
    _authorized(request)
    checkpoint = body.get("checkpoint")
    if not isinstance(checkpoint, dict):
        raise HTTPException(status_code=422, detail="CHECKPOINT_OBJECT_REQUIRED")
    try:
        return _machine_or_404(machine_id).restore_checkpoint(checkpoint)
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=422, detail={"code": "CHECKPOINT_REJECTED", "error": str(exc)}) from exc


@router.post("/machines/{machine_id}/faults")
def inject_virtual_machine_fault(machine_id: str, request: Request, body: dict):
    _authorized(request)
    machine = _machine_or_404(machine_id)
    try:
        return {"ok": True, "machine_id": machine_id,
                "result": machine.inject_fault(str(body["component"]), str(body["fault"]),
                                               int(body["address"]) if body.get("address") is not None else None)}
    except (KeyError, ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail={"code": "FAULT_INJECTION_REJECTED", "error": str(exc)}) from exc


@router.get("/server-fabric/profiles")
def list_virtual_server_profiles():
    """Read-only server profile catalog; profiles do not allocate host resources."""
    return {"ok": True, "profiles": list_server_profiles(),
            "fidelity": "SIMULATED", "host_resources_allocated": False}


@router.get("/server-fabric/backends")
def inspect_server_backends(request: Request):
    _authorized(request)
    return {"ok": True, **discover_backends()}


@router.get("/server-fabric/host-capacity")
def inspect_server_host_capacity(request: Request):
    _authorized(request)
    return {"ok": True, "host_capacity": observe_host_capacity().describe(),
            "resources_reserved": False, "vm_started": False}


@router.post("/server-fabric/admission")
def check_server_workload_admission(request: Request, body: dict):
    _authorized(request)
    profile_id = body.get("profile_id")
    if not isinstance(profile_id, str) or not profile_id.strip():
        raise HTTPException(status_code=422, detail="PROFILE_ID_REQUIRED")
    try:
        profile = get_server_profile(profile_id)
        host = observe_host_capacity()
        result = admit_server_workload(
            profile, host,
            memory_reserve_mib=int(body.get("memory_reserve_mib", 256)),
            disk_reserve_bytes=int(body.get("disk_reserve_bytes", 1024 * 1024 * 1024)),
            max_cpu_fraction=float(body.get("max_cpu_fraction", 0.75)),
        )
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail={"code": "SERVER_ADMISSION_REJECTED",
                                                     "error": str(exc)}) from exc
    return {"ok": result["ok"], "admission": result,
            "resources_reserved": False, "vm_started": False}


@router.post("/machines/{machine_id}/shutdown")
def shutdown_virtual_machine(machine_id: str, request: Request):
    _authorized(request)
    return {"ok": True, "machine_id": machine_id, "status": _machine_or_404(machine_id).shutdown()}
