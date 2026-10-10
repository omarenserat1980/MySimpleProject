"""HTTP API for persistent Golden Mission Loop tracking."""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from .brain.golden_mission import GoldenMissionController
from .brain.control_auth import require_control_key


class MissionCreate(BaseModel):
    title: str
    objective: str
    acceptance: list[str] = Field(min_length=1)
    estimate_minutes: int = Field(default=30, ge=1, le=10080)
    update_minutes: int = Field(default=15, ge=1, le=1440)
    max_attempts: int = Field(default=3, ge=1, le=10)


class PermissionRequest(BaseModel):
    permission: str
    detail: str = ""


class PermissionGrant(BaseModel):
    permission: str
    approved_by: str


class CheckpointRequest(BaseModel):
    summary: str
    progress: int = Field(ge=0, le=99)
    next_estimate_minutes: int | None = Field(default=None, ge=1, le=10080)
    evidence: dict | None = None


class CloseRequest(BaseModel):
    evidence_id: str
    evidence_sha256: str
    summary: str = ""


def router(controller: GoldenMissionController | None = None):
    c = controller or GoldenMissionController()
    r = APIRouter(prefix="/api/golden-missions", tags=["golden-missions"])

    @r.post("")
    def create(request: Request, body: MissionCreate):
        require_control_key(request)
        try:
            return {"ok": True, "mission": c.create(**body.model_dump())}
        except ValueError as exc:
            raise HTTPException(422, str(exc))

    @r.get("/due")
    def due(request: Request):
        require_control_key(request)
        return {"ok": True, "missions": c.list_due()}

    @r.get("/{mission_id}")
    def get(mission_id: str, request: Request):
        require_control_key(request)
        try:
            return {"ok": True, "mission": c.get(mission_id)}
        except KeyError:
            raise HTTPException(404, "MISSION_NOT_FOUND")

    @r.post("/{mission_id}/start")
    def start(mission_id: str, request: Request):
        require_control_key(request)
        try:
            return {"ok": True, "mission": c.start(mission_id)}
        except KeyError:
            raise HTTPException(404, "MISSION_NOT_FOUND")
        except ValueError as exc:
            raise HTTPException(409, str(exc))

    @r.post("/{mission_id}/permission-required")
    def permission_required(mission_id: str, body: PermissionRequest, request: Request):
        require_control_key(request)
        try:
            return {"ok": True, "mission": c.require_permission(mission_id, body.permission, body.detail)}
        except KeyError:
            raise HTTPException(404, "MISSION_NOT_FOUND")
        except ValueError as exc:
            raise HTTPException(409, str(exc))

    @r.post("/{mission_id}/permission-grant")
    def permission_grant(mission_id: str, body: PermissionGrant, request: Request):
        require_control_key(request)
        try:
            return {"ok": True, "mission": c.grant_permission(mission_id, body.permission, body.approved_by)}
        except KeyError:
            raise HTTPException(404, "MISSION_NOT_FOUND")
        except ValueError as exc:
            raise HTTPException(409, str(exc))

    @r.post("/{mission_id}/checkpoint")
    def checkpoint(mission_id: str, body: CheckpointRequest, request: Request):
        require_control_key(request)
        try:
            return {"ok": True, "mission": c.checkpoint(mission_id, **body.model_dump())}
        except KeyError:
            raise HTTPException(404, "MISSION_NOT_FOUND")
        except ValueError as exc:
            raise HTTPException(409, str(exc))

    @r.post("/{mission_id}/close")
    def close(mission_id: str, body: CloseRequest, request: Request):
        require_control_key(request)
        try:
            return {"ok": True, "mission": c.close(mission_id, **body.model_dump())}
        except KeyError:
            raise HTTPException(404, "MISSION_NOT_FOUND")
        except ValueError as exc:
            raise HTTPException(409, str(exc))

    return r
