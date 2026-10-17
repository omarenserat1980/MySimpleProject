"""Read-only-contract API for Brain's local ASIC logic simulator."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from .asic_hardware_simulator import ASICLogicSimulator, ASICSimulationError
from .asic_resource_adapter import ASICResource

router = APIRouter(prefix="/api/asic-sim", tags=["ASIC Simulator"])


class ASICRunRequest(BaseModel):
    netlist: dict
    vectors: list[dict] = Field(min_items=1, max_items=10000)
    max_cycles: int = Field(default=10000, ge=1, le=10000)


class SHA256dPowSimulationRequest(BaseModel):
    header_hex: str = Field(min_length=160, max_length=160)
    target_hex: str = Field(min_length=1, max_length=64)
    start_nonce: int = Field(default=0, ge=0, le=0xFFFFFFFF)
    max_attempts: int = Field(default=1000, ge=1, le=1_000_000)
    resource_id: str = Field(default="brain-sha256d-sim", min_length=1, max_length=128)

    @field_validator("header_hex")
    @classmethod
    def validate_header_hex(cls, value: str) -> str:
        try:
            raw = bytes.fromhex(value)
        except ValueError as exc:
            raise ValueError("INVALID_HEADER_HEX") from exc
        if len(raw) != 80:
            raise ValueError("HEADER_MUST_BE_EXACTLY_80_BYTES")
        return value.lower()

    @field_validator("target_hex")
    @classmethod
    def validate_target_hex(cls, value: str) -> str:
        try:
            target = int(value, 16)
        except ValueError as exc:
            raise ValueError("INVALID_TARGET_HEX") from exc
        if not 0 <= target < (1 << 256):
            raise ValueError("TARGET_MUST_BE_256_BIT_UNSIGNED")
        return value.lower()

    @field_validator("resource_id")
    @classmethod
    def validate_resource_id(cls, value: str) -> str:
        if not value.strip() or any(ord(char) < 32 for char in value):
            raise ValueError("INVALID_RESOURCE_ID")
        return value.strip()


@router.get("/status")

class SHA256dRtlSelfTestRequest(BaseModel):
    resource_id: str = Field(default="brain-sha256d-rtl-sim", min_length=1, max_length=128)
    timeout_seconds: float = Field(default=20.0, ge=0.1, le=120.0)

    @field_validator("resource_id")
    @classmethod
    def validate_rtl_resource_id(cls, value: str) -> str:
        if not value.strip() or any(ord(char) < 32 for char in value):
            raise ValueError("INVALID_RESOURCE_ID")
        return value.strip()

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


@router.post("/sha256d-pow")
def asic_sha256d_pow_simulation(body: SHA256dPowSimulationRequest, request: Request):
    """Run bounded real software hashes through Brain's ASIC simulation resource."""
    supervisor = getattr(request.app.state, "brain_supervisor", None)
    adapter = getattr(supervisor, "asic_resources", None)
    if adapter is None:
        raise HTTPException(
            status_code=503,
            detail={"status": "BRAIN_ASIC_RUNTIME_NOT_WIRED"},
        )
    resource = adapter.resources.get(body.resource_id)
    if resource is None:
        resource = ASICResource(resource_id=body.resource_id, execution_mode="SIMULATOR")
        adapter.register(resource)
    elif resource.execution_mode != "SIMULATOR":
        raise HTTPException(
            status_code=403,
            detail={"status": "SIMULATION_MODE_REQUIRED"},
        )
    try:
        return adapter.simulate_sha256d_pow(
            body.resource_id,
            header=bytes.fromhex(body.header_hex),
            target=int(body.target_hex, 16),
            start_nonce=body.start_nonce,
            max_attempts=body.max_attempts,
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/sha256d-rtl-self-test")
def asic_sha256d_rtl_self_test(body: SHA256dRtlSelfTestRequest, request: Request):
    """Run the actual repository RTL testbench; never substitute software hashing."""
    supervisor = getattr(request.app.state, "brain_supervisor", None)
    adapter = getattr(supervisor, "asic_resources", None)
    if adapter is None:
        raise HTTPException(status_code=503, detail={"status": "BRAIN_ASIC_RUNTIME_NOT_WIRED"})
    resource = adapter.resources.get(body.resource_id)
    if resource is None:
        resource = ASICResource(resource_id=body.resource_id, execution_mode="SIMULATOR")
        adapter.register(resource)
    elif resource.execution_mode != "SIMULATOR":
        raise HTTPException(status_code=403, detail={"status": "SIMULATION_MODE_REQUIRED"})
    try:
        result = adapter.simulate_sha256d_rtl(
            body.resource_id, timeout_seconds=body.timeout_seconds
        )
        status = result.get("result", {}).get("status", "UNKNOWN")
        if status != "VERIFIED":
            return {**result, "ok": False, "status": status}
        return {**result, "ok": True, "status": "RTL_SIMULATION_VERIFIED"}
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

