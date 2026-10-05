"""HTTP surface for the Synthetic Customer test client."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .brain.synthetic_customer import SyntheticCustomer

class CustomerRequest(BaseModel):
    customer_type: str
    request: str

def router(customer: SyntheticCustomer, capability_provider=None):
    r = APIRouter(prefix="/api/synthetic-customer", tags=["synthetic-customer"])

    @r.post("/runs")
    def create_run(body: CustomerRequest):
        run = customer.start(body.customer_type, body.request)
        capabilities = capability_provider() if capability_provider else {}
        proposals = customer.generate_proposals(run, capabilities)
        return {"ok": True, "run": run.__dict__, "proposals": proposals}

    @r.get("/runs/{run_id}")
    def get_run(run_id: str):
        try:
            return {"ok": True, "run": customer.get(run_id).__dict__}
        except KeyError:
            raise HTTPException(404, "SYNTHETIC_RUN_NOT_FOUND")

    @r.post("/runs/{run_id}/approve")
    def approve(run_id: str):
        try:
            run = customer.approve(customer.get(run_id))
            return {"ok": True, "run": run.__dict__}
        except KeyError:
            raise HTTPException(404, "SYNTHETIC_RUN_NOT_FOUND")
        except ValueError as exc:
            raise HTTPException(409, str(exc))

    @r.post("/payment-safety")
    def payment_safety(environment: str, payment_mode: str = "NONE"):
        return customer.safety_gate(environment, payment_mode)

    return r
