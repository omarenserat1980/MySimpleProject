"""FastAPI bridge for the cognitive orchestrator.

This module is framework-light: import it from main.py and mount the router.
"""
from typing import Any
from fastapi import APIRouter
from pydantic import BaseModel, Field
from .cognitive_orchestrator import CognitiveOrchestrator

router = APIRouter(prefix="/api/autonomous", tags=["autonomous"])
orchestrator = CognitiveOrchestrator()

class CycleRequest(BaseModel):
    objective: str = "inspect and improve current state"
    gaps: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=lambda: ["inspect"])
    expected: Any = None
    horizon: int = 5

class ImprovementRequest(BaseModel):
    id: str
    description: str

@router.get("/status")
def autonomous_status():
    return orchestrator.status()

@router.post("/cycle")
def autonomous_cycle(req: CycleRequest):
    return orchestrator.step(req.model_dump())

@router.post("/improvement")
def propose_improvement(req: ImprovementRequest):
    p = orchestrator.propose_improvement(req.id, req.description)
    return {"id": p.id, "description": p.description, "status": p.status}
