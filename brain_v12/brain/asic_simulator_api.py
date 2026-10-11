"""Read-only-contract API for Brain's local ASIC logic simulator."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .asic_hardware_simulator import ASICLogicSimulator, ASICSimulationError

router = APIRouter(prefix="/api/asic-sim", tags=["ASIC Simulator"])


class ASICRunRequest(BaseModel):
    netlist: dict
    vectors: list[dict] = Field(min_items=1, max_items=10000)
    max_cycles: int = Field(default=10000, ge=1, le=10000)


@router.get("/status")
def asic_simulator_status():
    return {
        "ok": True,
        "name": "Brain ASIC Logic Simulator",
        "version": "0.1.0",
        "model": "IDEAL_2_STATE_DIGITAL",
        "network_access": False,
        "hardware_access": False,
        "real_hardware_measurement": False,
        "supported_ops": ["INPUT", "CONST", "NOT", "BUF", "AND", "OR", "XOR", "NAND", "NOR", "XNOR", "MUX", "DFF"],
    }


@router.post("/run")
def asic_simulator_run(body: ASICRunRequest):
    try:
        simulator = ASICLogicSimulator(body.netlist)
        return simulator.run(body.vectors, max_cycles=body.max_cycles)
    except ASICSimulationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
