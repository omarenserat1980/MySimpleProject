"""Authenticated API for isolated Windows Server 2025 simulation sessions.

Run reports are persisted locally and explicitly synthetic. This router never invokes
a real executor, hypervisor, cloud API, or host agent.
"""
from __future__ import annotations

import json
import os
import re
import threading
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .control_auth import require_control_key
from .windows_server_2025_simulation_factory import (
    SCENARIOS,
    VirtualHardwareModel,
    WindowsServer2025Simulator,
    EvidenceRecorder,
)

router = APIRouter(prefix="/api/simulations/windows-server-2025",
                   tags=["windows-server-2025-simulation"])
_LOCK = threading.RLock()
_RUNS: dict[str, dict[str, Any]] = {}


def _state_dir() -> Path:
    configured = os.getenv("BRAIN_SIMULATION_STATE_DIR", "").strip()
    return Path(configured) if configured else (
        Path(__file__).resolve().parents[2] / ".brain" / "state" /
        "windows_server_2025_simulations"
    )


def _run_path(run_id: str) -> Path:
    if not re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", run_id):
        raise HTTPException(status_code=400, detail="INVALID_SIMULATION_RUN_ID")
    return _state_dir() / (run_id + ".json")


def _save_run(result: dict[str, Any]) -> None:
    path = _run_path(result["run_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(result, sort_keys=True, indent=2), encoding="utf-8")
    temporary.replace(path)


class SimulationRequest(BaseModel):
    scenario_id: str = "success"
    hardware: dict[str, Any] = Field(default_factory=dict)

    class Config:
        extra = "forbid"


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
    try:
        _save_run(result)
    except OSError as exc:
        raise HTTPException(status_code=503, detail="SIMULATION_EVIDENCE_WRITE_FAILED") from exc
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
    path = _run_path(run_id)
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="SIMULATION_RUN_NOT_FOUND") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=503, detail="SIMULATION_EVIDENCE_UNREADABLE") from exc
    if not isinstance(result, dict) or result.get("run_id") != run_id:
        raise HTTPException(status_code=503, detail="SIMULATION_EVIDENCE_INVALID")
    if result.get("execution_mode") != "SIMULATION_ONLY" or result.get("real_windows_boot_verified") is not False:
        raise HTTPException(status_code=503, detail="SIMULATION_REALITY_BOUNDARY_INVALID")
    verification = EvidenceRecorder.verify(result.get("events", []))
    if not verification.get("ok"):
        raise HTTPException(status_code=503, detail="SIMULATION_EVIDENCE_INVALID")
    with _LOCK:
        _RUNS[run_id] = result
    return result


@router.get("/dashboard", include_in_schema=False)
def simulation_dashboard() -> FileResponse:
    """Serve the local dashboard; API data endpoints still require control-key auth."""
    page = Path(__file__).resolve().parents[1] / "web" / "windows_server_2025_simulation.html"
    if not page.is_file():
        raise HTTPException(status_code=404, detail="SIMULATION_DASHBOARD_NOT_FOUND")
    return FileResponse(page, media_type="text/html")


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
