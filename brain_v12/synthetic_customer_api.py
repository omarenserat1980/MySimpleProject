"""HTTP surface for the Synthetic Customer test client."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .brain.synthetic_customer import SyntheticCustomer


class CustomerRequest(BaseModel):
    customer_type: str
    request: str


class CustomerExecuteRequest(BaseModel):
    environment: str = "TEST"
    payment_mode: str = "NONE"


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

    @r.post("/runs/{run_id}/execute")
    def execute(run_id: str, body: CustomerExecuteRequest):
        try:
            run = customer.execute(
                customer.get(run_id),
                environment=body.environment,
                payment_mode=body.payment_mode,
            )
            return {"ok": run.status == "VERIFIED", "run": run.__dict__}
        except KeyError:
            raise HTTPException(404, "SYNTHETIC_RUN_NOT_FOUND")
        except ValueError as exc:
            raise HTTPException(409, str(exc))

    class CustomerReviewRequest(BaseModel):
        accepted: bool
        feedback: str = ""

    class CustomerRevisionRequest(BaseModel):
        feedback: str

    @r.post("/runs/{run_id}/review")
    def review(run_id: str, body: CustomerReviewRequest):
        try:
            run = customer.review(customer.get(run_id), body.accepted, body.feedback)
            return {"ok": True, "run": run.__dict__}
        except KeyError:
            raise HTTPException(404, "SYNTHETIC_RUN_NOT_FOUND")
        except ValueError as exc:
            raise HTTPException(409, str(exc))

    @r.post("/runs/{run_id}/revise")
    def revise(run_id: str, body: CustomerRevisionRequest):
        try:
            run = customer.revise(customer.get(run_id), body.feedback)
            return {"ok": True, "run": run.__dict__}
        except KeyError:
            raise HTTPException(404, "SYNTHETIC_RUN_NOT_FOUND")
        except ValueError as exc:
            raise HTTPException(409, str(exc))

    @r.post("/runs/{run_id}/deliver")
    def deliver(run_id: str):
        try:
            run = customer.deliver(customer.get(run_id))
            return {"ok": True, "run": run.__dict__}
        except KeyError:
            raise HTTPException(404, "SYNTHETIC_RUN_NOT_FOUND")
        except ValueError as exc:
            raise HTTPException(409, str(exc))

    @r.post("/payment-safety")
    def payment_safety(environment: str, payment_mode: str = "NONE"):
        return customer.safety_gate(environment, payment_mode)

    return r
