"""FastAPI routes for BRAIN Cloud Fabric."""
from __future__ import annotations
import os, hmac
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

from cloud.brain_fabric import (
    register_node, heartbeat, list_nodes, choose_node, create_job,
    get_job, transition_job, snapshot, update_node, next_node_job,
)
from cloud.brain_node_security import create_enrollment, verify_enrollment

router = APIRouter(prefix="/v1/fabric", tags=["brain-fabric"])

def fabric_auth(
    request: Request,
    authorization: str | None = Header(default=None),
    local_app: str | None = Header(default=None, alias="X-BRAIN-Local-App"),
) -> None:
    host = request.client.host if request.client else ""
    if local_app == "1" and host in {"127.0.0.1", "::1", "localhost"}:
        return
    token = os.getenv("BRAIN_CONTROL_TOKEN", "")
    if not token or not authorization or not hmac.compare_digest(authorization, "Bearer "+token):
        raise HTTPException(status_code=401, detail="unauthorized")

class NodeRequest(BaseModel):
    node_id: str
    provider: str = "self-hosted"
    architecture: str = "unknown"
    cpu: float = 0
    memory_mb: int = 0
    storage_gb: int = 0
    capabilities: list[str] = Field(default_factory=list)
    endpoint: str | None = None

class EnrollmentRequest(BaseModel):
    node_id: str
    ttl_seconds: int = 900

class HeartbeatRequest(BaseModel):
    enrollment_token: str
    state: str = "READY"
    jobs_running: int = 0
    architecture: str | None = None
    cpu: float | None = None
    memory_mb: int | None = None
    storage_gb: int | None = None
    capabilities: list[str] | None = None

class JobRequest(BaseModel):
    kind: str
    payload: dict = Field(default_factory=dict)
    required_capabilities: list[str] = Field(default_factory=list)

class TransitionRequest(BaseModel):
    state: str
    evidence: dict | None = None

@router.get("", dependencies=[Depends(fabric_auth)])
def fabric_status():
    return {"ok": True, **snapshot()}

@router.post("/enroll", dependencies=[Depends(fabric_auth)])
def enroll(body: EnrollmentRequest):
    return {"ok": True, **create_enrollment(body.node_id.strip(), body.ttl_seconds)}

@router.post("/nodes", dependencies=[Depends(fabric_auth)])
def add_node(body: NodeRequest):
    return {"ok": True, "node": register_node(
        body.node_id, provider=body.provider, architecture=body.architecture,
        cpu=body.cpu, memory_mb=body.memory_mb, storage_gb=body.storage_gb,
        capabilities=body.capabilities, endpoint=body.endpoint)}

@router.get("/nodes", dependencies=[Depends(fabric_auth)])
def nodes():
    return {"ok": True, "nodes": list_nodes()}

@router.get("/nodes/{node_id}/jobs/next")
def node_next_job(node_id: str, authorization: str | None = Header(default=None)):
    token = authorization[7:].strip() if authorization and authorization.startswith("Bearer ") else ""
    if not verify_enrollment(node_id, token):
        raise HTTPException(status_code=401, detail="invalid or expired enrollment token")
    job = next_node_job(
        node_id,
        required_capabilities=["windows-server-2025", "windows-cloud", "brain-task-execution"],
    )
    return {"ok": True, "job": job}

@router.post("/nodes/{node_id}/jobs/{job_id}/result")
def node_job_result(
    node_id: str,
    job_id: str,
    body: TransitionRequest,
    authorization: str | None = Header(default=None),
):
    token = authorization[7:].strip() if authorization and authorization.startswith("Bearer ") else ""
    if not verify_enrollment(node_id, token):
        raise HTTPException(status_code=401, detail="invalid or expired enrollment token")
    job = get_job(job_id)
    if not job or job.get("node_id") != node_id:
        raise HTTPException(status_code=404, detail="node job not found")
    if body.state not in {"SUCCESS", "FAILED", "CANCELLED", "RETRYING"}:
        raise HTTPException(status_code=400, detail="invalid terminal job state")
    try:
        result = transition_job(job_id, body.state, evidence=body.evidence)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True, "job": result}

@router.post("/nodes/{node_id}/heartbeat")
def node_heartbeat(node_id: str, body: HeartbeatRequest):
    if not verify_enrollment(node_id, body.enrollment_token):
        raise HTTPException(status_code=401, detail="invalid or expired enrollment token")
    try:
        result = heartbeat(node_id, state=body.state, jobs_running=body.jobs_running)
    except KeyError:
        result = register_node(
            node_id, architecture=body.architecture or "unknown",
            cpu=body.cpu or 0, memory_mb=body.memory_mb or 0,
            storage_gb=body.storage_gb or 0, capabilities=body.capabilities or [])
    else:
        result = update_node(
            node_id,
            architecture=body.architecture,
            cpu=body.cpu,
            memory_mb=body.memory_mb,
            storage_gb=body.storage_gb,
            capabilities=body.capabilities,
        )
    return {"ok": True, "node": result}

@router.post("/choose", dependencies=[Depends(fabric_auth)])
def choose(body: JobRequest):
    return {"ok": True, "node": choose_node(body.required_capabilities)}

@router.post("/jobs", dependencies=[Depends(fabric_auth)])
def job_create(body: JobRequest):
    try:
        return {"ok": True, "job": create_job(body.kind, body.payload, body.required_capabilities)}
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

@router.get("/jobs/{job_id}", dependencies=[Depends(fabric_auth)])
def job_get(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="fabric job not found")
    return {"ok": True, "job": job}

@router.post("/jobs/{job_id}/transition", dependencies=[Depends(fabric_auth)])
def job_transition(job_id: str, body: TransitionRequest):
    try:
        return {"ok": True, "job": transition_job(job_id, body.state, evidence=body.evidence)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="fabric job not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
