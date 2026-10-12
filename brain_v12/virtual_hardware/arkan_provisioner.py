"""Canonical, simulation-first Arkan virtual-computer provisioning.

This module persists logical identity and configuration. It does not provision a
native guest OS, allocate host resources equal to modeled capacities, or start a
hypervisor. The internal VirtualComputer is a deterministic simulator.
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .computer import VirtualComputer

ARKAN_NAME = "Arkan"
ARKAN_ID = "arkan-virtual-01"
SCHEMA_VERSION = 1
DEFAULT_CONFIG: dict[str, Any] = {
    "ram_size": 65536,
    "storage_size": 16 * 1024 * 1024,
    "external_network_enabled": False,
}
REGISTRY_ENV = "BRAIN_ARKAN_REGISTRY_PATH"


def default_registry_path() -> Path:
    configured = os.environ.get(REGISTRY_ENV)
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".brain" / "virtual-machines" / f"{ARKAN_ID}.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json_atomically(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def read_arkan_record(path: str | os.PathLike[str] | None = None) -> dict[str, Any] | None:
    """Read the canonical persisted identity record; never invent a missing record."""
    target = Path(path).expanduser() if path is not None else default_registry_path()
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("ARKAN_REGISTRY_UNREADABLE") from exc
    if not isinstance(data, dict) or data.get("device_id") != ARKAN_ID:
        raise ValueError("ARKAN_REGISTRY_IDENTITY_INVALID")
    return data


def provision_arkan(
    path: str | os.PathLike[str] | None = None,
    machine: VirtualComputer | None = None,
) -> dict[str, Any]:
    """Idempotently reconcile Arkan's logical identity and boot the simulator.

    Returns the same canonical ID on repeated calls. Existing runtime instances
    may be supplied by the API layer. Persisted state is identity/configuration
    evidence only; it is not a serialized guest OS or a native VM disk.
    """
    target = Path(path).expanduser() if path is not None else default_registry_path()
    if machine is not None and machine.name != ARKAN_ID:
        raise ValueError("ARKAN_MACHINE_ID_MISMATCH")

    active = machine or VirtualComputer(name=ARKAN_ID, **DEFAULT_CONFIG)
    validation = active.validate_configuration()
    if not validation.get("ok"):
        raise ValueError("ARKAN_HARDWARE_MANIFEST_INVALID")
    if not active.powered:
        active.power_on()

    # A bounded symbolic workload proves simulator task execution only.
    active.cpu.reset()
    smoke_test = active.execute(
        [("MOVI", 0, 1), ("OUT", 0), ("HALT",)],
        max_cycles=10,
    )
    if smoke_test.get("output") != [1] or not smoke_test.get("halted"):
        raise RuntimeError("ARKAN_SIMULATOR_SMOKE_TEST_FAILED")

    previous = read_arkan_record(target)
    now = _utc_now()
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "device_name": ARKAN_NAME,
        "device_id": ARKAN_ID,
        "device_type": "virtual_computer",
        "owner": "Electronic Brain",
        "execution_mode": "software_defined",
        "lifecycle": "ready",
        "readiness": "SIMULATION_READY",
        "identity_scope": "independent_of_physical_host",
        "execution_backend": "brain-simulator",
        "backend_mode": "SIMULATED",
        "host_binding": None,
        "host_dependencies_for_identity": False,
        "hardware_manifest": active.hardware_manifest(),
        "configuration_fingerprint": active.configuration_fingerprint(),
        "runtime_status": active.status(),
        "task_execution_evidence": {
            "status": "PASS",
            "workload": "bounded_symbolic_cpu_smoke",
            "output_expected": [1],
            "output_observed": smoke_test.get("output"),
            "cycles": smoke_test.get("cycles"),
            "fidelity": "SIMULATED",
        },
        "os_target": {
            "product": "Windows Server",
            "version": "2025",
            "installation_status": "NOT_INSTALLED",
            "boot_status": "NOT_VERIFIED",
            "native_guest": False,
        },
        "claims": {
            "physical_capacity_claimed": False,
            "native_os_boot_verified": False,
            "hypervisor_started": False,
            "external_network_enabled": False,
        },
        "provisioning": {
            "status": "RECONCILED",
            "created_at": previous.get("provisioning", {}).get("created_at", now) if previous else now,
            "updated_at": now,
            "idempotent": True,
        },
        "registry_path": str(target),
    }
    _write_json_atomically(target, record)
    return {"record": record, "machine": active}


def arkan_status(path: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    """Return persisted status without claiming the simulator is loaded in memory."""
    record = read_arkan_record(path)
    if record is None:
        return {
            "ok": True,
            "exists": False,
            "device_id": ARKAN_ID,
            "lifecycle": "stopped",
            "readiness": "NOT_PROVISIONED",
            "native_os_boot_verified": False,
        }
    return {
        "ok": True,
        "exists": True,
        "device_id": ARKAN_ID,
        "device_name": ARKAN_NAME,
        "lifecycle": record.get("lifecycle", "failed"),
        "readiness": record.get("readiness", "UNKNOWN"),
        "execution_backend": record.get("execution_backend"),
        "host_dependencies_for_identity": record.get("host_dependencies_for_identity") is False,
        "os_target": record.get("os_target"),
        "claims": record.get("claims"),
        "task_execution_evidence": record.get("task_execution_evidence", {}),
        "configuration_fingerprint": record.get("configuration_fingerprint"),
        "registry_path": record.get("registry_path"),
        "runtime_state_persisted": False,
        "native_os_boot_verified": False,
    }
