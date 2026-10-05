"""API for Synthetic Customer proposal/approval test runs."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .brain.synthetic_customer import SyntheticCustomer, Proposal

class CustomerRequest(BaseModel):
    customer_type:str
    request:str

class ProposalIn(BaseModel):
    source:str
    summary:str=""
    scope:list[str]=[]
    risks:list[str]=[]
    acceptance:list[str]=[]
    requires_approval:bool=True

class ApprovalIn(BaseModel):
    proposal:dict

def router(customer:SyntheticCustomer):
    r=APIRouter(prefix="/api/synthetic-customer",tags=["synthetic-customer"])

    @r.post("/runs")
    def create_run(body:CustomerRequest):
        run=customer.start(body.customer_type,body.request)
        return {"ok":True,"run":run.__dict__}

    @r.post("/runs/{run_id}/proposals/merge")
    def merge(run_id:str, body:list[ProposalIn]):
        if len(body)!=2:
            raise HTTPException(400,"CHATGPT_AND_BRAIN_PROPOSALS_REQUIRED")
        p=customer.merge_proposals(
            Proposal(**body[0].model_dump()),Proposal(**body[1].model_dump()))
        return {"ok":True,"run_id":run_id,"proposal":p}

    @r.post("/runs/{run_id}/approve")
    def approve(run_id:str, body:ApprovalIn):
        # This endpoint is intentionally a test approval only; execution remains separate.
        return {"ok":True,"run_id":run_id,"status":"APPROVED_FOR_TEST_EXECUTION","proposal":body.proposal}

    @r.post("/payment-safety")
    def payment_safety(environment:str,payment_mode:str="NONE"):
        return customer.safety_gate(environment,payment_mode)

    return r
