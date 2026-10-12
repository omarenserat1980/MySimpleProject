from fastapi import APIRouter
from pydantic import BaseModel, Field

class FabricExecuteIn(BaseModel):
    task: str
    payload: dict = Field(default_factory=dict)
    kind: str = "model"

class FabricConsensusIn(BaseModel):
    task: str
    payload: dict = Field(default_factory=dict)
    min_agreement: int = 2

def router(fabric):
    r = APIRouter(prefix="/api/ai-fabric", tags=["Brain AI Fabric"])
    @r.get("/status")
    def status(): return fabric.registry()
    @r.post("/execute")
    def execute(body: FabricExecuteIn): return fabric.execute(body.task, body.payload, body.kind)
    @r.post("/consensus")
    def consensus(body: FabricConsensusIn): return fabric.consensus(body.task, body.payload, body.min_agreement)
    return r
