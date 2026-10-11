"""Read-only API for Brain's device-backed software cloud."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from .device_cloud_pool import DeviceCloudPool
from .portable_resource_orchestrator import ResourceDemand


class CloudPlanRequest(BaseModel):
    task_id: str
    capability: str
    cpu_cores: float = 1.0
    memory_mb: int = 512
    disk_mb: int = 256
    gpu_count: int = 0
    timeout_seconds: int = 300


def build_router(pool: DeviceCloudPool) -> APIRouter:
    router = APIRouter(prefix="/api/cloud-pool", tags=["cloud-pool"])

    @router.get("/status")
    def status():
        return pool.status()

    @router.post("/plan")
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

    return router
