"""Authenticated Brain control-plane API for cloud executor attestations.

Deploy only on the Brain control-plane service. Per-executor bearer tokens are
configured out of band; the runner never receives the signing private key.
"""
from __future__ import annotations
import hmac, json, os
from pathlib import Path
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from .cloud_executor_attestation_issuer import create_challenge, issue_attestation, consume_issued_attestation

router = APIRouter(prefix="/api/cloud-executor/attestation", tags=["cloud-executor-attestation"])

class ExecutorRequest(BaseModel):
    executor_id: str = Field(min_length=1, max_length=200)

class IssueRequest(ExecutorRequest):
    nonce: str = Field(min_length=32, max_length=256)

class ConsumeRequest(ExecutorRequest):
    nonce: str = Field(min_length=32, max_length=256)

def _registry_db() -> str:
    path = os.environ.get("BRAIN_CLOUD_EXECUTOR_REGISTRY_DB", os.environ.get("BRAIN_DB", "/var/lib/brain/cloud-executor-registry.sqlite3"))
    if Path(path).is_symlink():
        raise HTTPException(status_code=503, detail="CLOUD_EXECUTOR_REGISTRY_PATH_INVALID")
    if not Path(path).parent.is_dir():
        raise HTTPException(status_code=503, detail="CLOUD_EXECUTOR_REGISTRY_PARENT_MISSING")
    return path

def _authenticate(executor_id: str, token: str) -> None:
    if not token:
        raise HTTPException(status_code=401, detail="CLOUD_EXECUTOR_AUTH_REQUIRED")
    try:
        enrollments = json.loads(os.environ.get("BRAIN_CLOUD_EXECUTOR_ENROLLMENTS_JSON", "{}"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=503, detail="CLOUD_EXECUTOR_ENROLLMENTS_CONFIG_INVALID") from exc
    expected = enrollments.get(executor_id) if isinstance(enrollments, dict) else None
    if not isinstance(expected, str) or not expected or not hmac.compare_digest(expected, token):
        raise HTTPException(status_code=403, detail="CLOUD_EXECUTOR_AUTH_REJECTED")

@router.post("/challenge")
def attestation_challenge(body: ExecutorRequest, x_brain_executor_token: str = Header(default="", alias="X-Brain-Executor-Token")):
    _authenticate(body.executor_id, x_brain_executor_token)
    if not os.environ.get("BRAIN_EXECUTOR_ATTESTATION_SIGNING_KEY_B64"):
        raise HTTPException(status_code=503, detail="CLOUD_EXECUTOR_ISSUER_NOT_CONFIGURED")
    try:
        return create_challenge(authenticated_executor_id=body.executor_id, challenge_db_path=_registry_db())
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

@router.post("/issue")
def attestation_issue(body: IssueRequest, x_brain_executor_token: str = Header(default="", alias="X-Brain-Executor-Token")):
    _authenticate(body.executor_id, x_brain_executor_token)
    try:
        return issue_attestation(authenticated_executor_id=body.executor_id, challenge_nonce=body.nonce,
                                 challenge_db_path=_registry_db(), lifetime_seconds=300)
    except ValueError as exc:
        code = str(exc)
        status = 403 if "MISMATCH" in code or "REPLAY" in code else 503
        raise HTTPException(status_code=status, detail=code) from exc

@router.post("/consume")
def attestation_consume(body: ConsumeRequest, x_brain_executor_token: str = Header(default="", alias="X-Brain-Executor-Token")):
    _authenticate(body.executor_id, x_brain_executor_token)
    try:
        return consume_issued_attestation(authenticated_executor_id=body.executor_id, nonce=body.nonce,
                                          registry_db_path=_registry_db())
    except ValueError as exc:
        code = str(exc)
        status = 403 if "MISMATCH" in code or "REPLAY" in code else 503
        raise HTTPException(status_code=status, detail=code) from exc
