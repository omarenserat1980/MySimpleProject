"""Protected Brain V7 API for the code workspace and control plane.

The API is the execution boundary between Brain reasoning and source code:
inspect, preview, verify, checkpoint, validated apply, and restore.

No endpoint accepts shell commands, credentials, arbitrary filesystem paths,
or direct money movement.
"""
from __future__ import annotations

from dataclasses import asdict
import os

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from .access_control import AccessController
from .code_workspace_tool import CodeChange, CodeWorkspaceTool
from .code_tool_engineering_team import CodeToolEngineeringTeam
from .employee_hierarchy import EmployeeHierarchy


router = APIRouter(prefix="/api/brain", tags=["brain-code"])
access = AccessController()
_workspace = CodeWorkspaceTool(
    root=os.getenv("BRAIN_CODE_ROOT") or os.getcwd(),
    allowed_prefixes=("brain_v7/",),
)
_team = CodeToolEngineeringTeam(EmployeeHierarchy(initial_employees=0), _workspace)


class ChangeIn(BaseModel):
    path: str = Field(min_length=1, max_length=240)
    content: str
    reason: str = ""


class ChangesIn(BaseModel):
    changes: list[ChangeIn] = Field(..., min_items=1, max_items=32)
    persist_to_github: bool = False
    commit_message: str = "Brain V7 code change"


class PathsIn(BaseModel):
    paths: list[str] = Field(default_factory=list, max_items=200)


def _identity(token: str | None):
    identity = access.authenticate(token)
    if identity is None:
        raise HTTPException(status_code=401, detail="BRAIN_API_KEY_REQUIRED")
    return identity


def _require(token: str | None, scope: str):
    identity = _identity(token)
    if not access.allowed(identity, scope):
        raise HTTPException(status_code=403, detail=f"SCOPE_REQUIRED:{scope}")
    return identity


def _changes(body: ChangesIn) -> list[CodeChange]:
    return [CodeChange(x.path, x.content, x.reason) for x in body.changes]


@router.get("/health")
def brain_health():
    return {
        "ok": True,
        "service": "Electronic Brain V7 Code API",
        "authentication": access.status(),
        "capabilities": {
            "inspect": True,
            "preview": True,
            "verify": True,
            "checkpoint": True,
            "restore": True,
            "validated_apply": True,
            "github_publish": True,
            "shell_execution": False,
            "credential_access": False,
            "money_movement": False,
        },
    }


@router.get("/auth/status")
def auth_status(x_brain_api_key: str | None = Header(default=None)):
    identity = _identity(x_brain_api_key)
    return {"ok": True, "key_id": identity.key_id, "scopes": sorted(identity.scopes)}


@router.get("/code")
def inspect_code(path: str, x_brain_api_key: str | None = Header(default=None)):
    _require(x_brain_api_key, "code:read")
    try:
        return {"ok": True, "path": path, "content": _workspace.read(path)}
    except (ValueError, PermissionError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/code/preview")
def preview_code(body: ChangesIn, x_brain_api_key: str | None = Header(default=None)):
    _require(x_brain_api_key, "code:preview")
    try:
        return _team.validate_change(_changes(body))
    except (ValueError, PermissionError, SyntaxError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/code/verify")
def verify_code(body: PathsIn, x_brain_api_key: str | None = Header(default=None)):
    _require(x_brain_api_key, "code:verify")
    return _team.verify(body.paths)


@router.post("/code/checkpoint")
def checkpoint(body: PathsIn, x_brain_api_key: str | None = Header(default=None)):
    _require(x_brain_api_key, "code:checkpoint")
    try:
        return _workspace.checkpoint(body.paths)
    except (ValueError, PermissionError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/code/apply")
def apply_code(body: ChangesIn, x_brain_api_key: str | None = Header(default=None)):
    identity = _require(x_brain_api_key, "code:write")
    if not access.write_enabled:
        raise HTTPException(status_code=423, detail="CODE_WRITE_DISABLED")
    if body.persist_to_github:
        if not access.publish_enabled:
            raise HTTPException(status_code=423, detail="GITHUB_PUBLISH_DISABLED")
        if not access.allowed(identity, "code:publish"):
            raise HTTPException(status_code=403, detail="SCOPE_REQUIRED:code:publish")
    if len(body.commit_message.strip()) < 4:
        raise HTTPException(status_code=400, detail="INVALID_COMMIT_MESSAGE")
    try:
        return _team.execute_autonomous_change(
            _changes(body),
            reason="Brain API authorized code change",
            commit_message=body.commit_message,
            remote=body.persist_to_github,
        )
    except (ValueError, PermissionError, RuntimeError, SyntaxError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/code/restore/{checkpoint_id}")
def restore_code(checkpoint_id: str, x_brain_api_key: str | None = Header(default=None)):
    _require(x_brain_api_key, "code:restore")
    try:
        results = _workspace.restore(checkpoint_id)
        return {"status": "RESTORED", "results": [asdict(x) for x in results]}
    except (ValueError, PermissionError, FileNotFoundError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/code/capabilities")
def code_capabilities(x_brain_api_key: str | None = Header(default=None)):
    _require(x_brain_api_key, "code:read")
    return _team.capability_status()


@router.get("/snapshot")
def snapshot(x_brain_api_key: str | None = Header(default=None)):
    _require(x_brain_api_key, "brain:read")
    return {
        "access": access.status(),
        "workspace": _workspace.snapshot(),
        "engineering_team": _team.snapshot(),
    }
