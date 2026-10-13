"""Authenticated API for isolated Windows Server 2025 simulation sessions.

All results are process-local and explicitly synthetic. This router never invokes
a real executor, hypervisor, cloud API, or host agent.
"""
from __future__ import annotations

import threading
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from .control_auth import require_control_key
from .windows_server_2025_simulation_factory import (
    SCENARIOS,
    VirtualHardwareModel,
    WindowsServer2025Simulator,
)

router = APIRouter(prefix="/api/simulations/windows-server-2025",
                   tags=["windows-server-2025-simulation"])
_LOCK = threading.RLock()
_RUNS: dict[str, dict[str, Any]] = {}


class SimulationRequest(BaseModel):
    scenario_id: str = "success"
    hardware: dict[str, Any] = Field(default_factory=dict)


@router.post("")
def create_simulation(payload: SimulationRequest, request: Request) -> dict[str, Any]:
    require_control_key(request)
    if payload.scenario_id not in SCENARIOS:
        raise HTTPException(status_code=422, detail="UNKNOWN_SIMULATION_SCENARIO")
    allowed = set(VirtualHardwareModel.__dataclass_fields__)
    if set(payload.hardware) - allowed:
        raise HTTPException(status_code=422, detail="UNKNOWN_VIRTUAL_HARDWARE_FIELD")
    try:
        hardware = VirtualHardwareModel(**payload.hardware)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="INVALID_VIRTUAL_HARDWARE") from exc
    result = WindowsServer2025Simulator(hardware).run(payload.scenario_id)
    with _LOCK:
        _RUNS[result["run_id"]] = result
    return {
        "ok": result["status"] in {"SIMULATED_BOOT_SUCCESS", "SIMULATED_BOOT_PARTIAL"},
        "run_id": result["run_id"],
        "status": result["status"],
        "execution_mode": "SIMULATION_ONLY",
        "real_windows_boot_verified": False,
        "report_url": f"/api/simulations/windows-server-2025/{result['run_id']}/report",
    }


def _get_run(run_id: str) -> dict[str, Any]:
    with _LOCK:
        result = _RUNS.get(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="SIMULATION_RUN_NOT_FOUND")
    return result


@router.get("/{run_id}")
def get_simulation(run_id: str, request: Request) -> dict[str, Any]:
    require_control_key(request)
    result = _get_run(run_id)
    return {key: value for key, value in result.items() if key != "events"}


@router.get("/{run_id}/events")
def get_simulation_events(run_id: str, request: Request) -> dict[str, Any]:
    require_control_key(request)
    result = _get_run(run_id)
    return {"run_id": run_id, "events": result["events"],
            "execution_mode": "SIMULATION_ONLY", "real_windows_boot_verified": False}


@router.get("/{run_id}/report")
def get_simulation_report(run_id: str, request: Request) -> dict[str, Any]:
    require_control_key(request)
    return _get_run(run_id)
