"""FastAPI bridge for the cognitive orchestrator."""
from typing import Any
from fastapi import APIRouter
from pydantic import BaseModel, Field
from .cognitive_orchestrator import CognitiveOrchestrator
from .agent_executor import execute_action

router = APIRouter(prefix="/api/autonomous", tags=["autonomous"])
orchestrator = CognitiveOrchestrator(action_executor=execute_action)

class CycleRequest(BaseModel):
    objective: str = "inspect and improve current state"
    gaps: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=lambda: ["inspect"])
    expected: Any = None
    horizon: int = 5

class LoopRequest(BaseModel):
    objective: str = "run bounded autonomous loop"
    gaps: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=lambda: ["inspect"])
    expected: Any = None
    action_expectations: dict[str, Any] = Field(default_factory=dict)
    horizon: int = 5

class ImprovementRequest(BaseModel):
    id: str
    description: str

@router.get("/status")
def autonomous_status():
    return orchestrator.status()

@router.post("/cycle")
def autonomous_cycle(req: CycleRequest):
    payload = req.model_dump() if hasattr(req, "model_dump") else req.dict()
    return orchestrator.step(payload)

@router.post("/loop")
def autonomous_loop(req: LoopRequest):
    payload = req.model_dump() if hasattr(req, "model_dump") else req.dict()
    return orchestrator.run_loop(payload)

@router.post("/improvement")
def propose_improvement(req: ImprovementRequest):
    p = orchestrator.propose_improvement(req.id, req.description)
    return {"id": p.id, "description": p.description, "status": p.status}
