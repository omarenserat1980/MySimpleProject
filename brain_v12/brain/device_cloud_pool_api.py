"""APIs for the device-backed pool and Brain-owned logical hardware leases."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from .control_auth import require_control_key
from .device_cloud_pool import DeviceCloudPool
from .portable_resource_orchestrator import ResourceDemand
from .software_hardware_factory import SoftwareHardwareFactory


class CloudPlanRequest(BaseModel):
    task_id: str
    capability: str
    cpu_cores: float = 1.0
    memory_mb: int = 512
    disk_mb: int = 256
    gpu_count: int = 0
    timeout_seconds: int = 300


class HardwarePlanRequest(BaseModel):
    task_id: str = Field(min_length=1, max_length=128)
    cpu_cores: float = Field(default=0.25, gt=0, le=128)
    memory_mb: int = Field(default=128, gt=0, le=1_048_576)
    disk_mb: int = Field(default=0, ge=0, le=1_048_576)


class HardwareAllocateRequest(HardwarePlanRequest):
    execute_self_test: bool = True
    test_rounds: int = Field(default=1000, ge=1, le=100_000)


class HardwareReleaseRequest(BaseModel):
    lease_id: str = Field(min_length=1, max_length=128)


class HardwareJobRequest(BaseModel):
    lease_id: str = Field(min_length=1, max_length=128)
    rounds: int = Field(default=1000, ge=1, le=100_000)


def build_router(pool: DeviceCloudPool) -> APIRouter:
    # Use explicit paths so the existing app can include one router while both
    # /api/cloud-pool and /api/hardware remain at their documented root paths.
    router = APIRouter(tags=["cloud-pool", "software-defined-hardware"])
    hardware = SoftwareHardwareFactory()

    @router.get("/api/cloud-pool/status")
    def status():
        return pool.status()

    @router.post("/api/cloud-pool/plan")
    def plan(body: CloudPlanRequest):
        decision = pool.plan(
            task_id=body.task_id,
            capability=body.capability,
            demand=ResourceDemand(
                cpu_cores=body.cpu_cores,
                memory_mb=body.memory_mb,
                disk_mb=body.disk_mb,
                gpu_count=body.gpu_count,
                timeout_seconds=body.timeout_seconds,
            ),
        )
        return decision.to_dict()

    @router.get("/api/hardware/status")
    def hardware_status():
        return hardware.status()

    @router.get("/api/hardware/resources")
    def hardware_resources():
        return hardware.resources()

    @router.get("/api/hardware/health")
    def hardware_health():
        state = hardware.status()
        return {
            "ok": True,
            "status": "HEALTHY" if state["capacity"]["cpu_cores_physical_observed"] > 0 else "DEGRADED",
            "execution_host": state["execution_host"],
            "resource_semantics": state["resource_semantics"],
            "remote_execution_proven": False,
        }

    @router.post("/api/hardware/plan")
    def hardware_plan(body: HardwarePlanRequest):
        try:
            return hardware.plan(
                task_id=body.task_id,
                cpu_cores=body.cpu_cores,
                memory_mb=body.memory_mb,
                disk_mb=body.disk_mb,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.post("/api/hardware/allocate")
    def hardware_allocate(request: Request, body: HardwareAllocateRequest):
        require_control_key(request)
        try:
            allocated = hardware.allocate(
                task_id=body.task_id,
                cpu_cores=body.cpu_cores,
                memory_mb=body.memory_mb,
                disk_mb=body.disk_mb,
            )
            if body.execute_self_test:
                allocated["execution"] = hardware.run_self_test(
                    allocated["lease"]["lease_id"], rounds=body.test_rounds
                )
            return allocated
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @router.post("/api/hardware/jobs")
    def hardware_run_job(request: Request, body: HardwareJobRequest):
        require_control_key(request)
        try:
            return hardware.run_self_test(body.lease_id, rounds=body.rounds)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @router.get("/api/hardware/jobs/{job_id}")
    def hardware_job(job_id: str):
        try:
            return hardware.job(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @router.post("/api/hardware/release")
    def hardware_release(request: Request, body: HardwareReleaseRequest):
        require_control_key(request)
        try:
            return hardware.release(body.lease_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    return router
