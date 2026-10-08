"""Revenue conversion API: delivery -> payment request -> reconciliation -> realization."""
from fastapi import APIRouter, Request
from pydantic import BaseModel

from .control_auth import require_control_key


class PaymentRequestBody(BaseModel):
    opportunity_id: str
    client_id: str
    amount_jod: float
    currency: str = "JOD"
    order_id: str | None = None


class PaymentReconcileBody(BaseModel):
    opportunity_id: str
    client_id: str
    amount_jod: float
    currency: str = "JOD"
    transaction_id: str
    evidence: str
    order_id: str | None = None


class RevenueRealizeBody(BaseModel):
    opportunity_id: str
    client_id: str


def router(lifecycle):
    r = APIRouter(prefix="/api/revenue-conversion", tags=["revenue-conversion"])

    @r.post("/request")
    def request_payment(request: Request, body: PaymentRequestBody):
        require_control_key(request)
        return lifecycle.request_payment(
            body.opportunity_id, body.amount_jod, body.currency,
            client_id=body.client_id, order_id=body.order_id,
        )

    @r.post("/reconcile")
    def reconcile(request: Request, body: PaymentReconcileBody):
        require_control_key(request)
        return lifecycle.reconcile_payment(
            body.opportunity_id, body.amount_jod, body.currency,
            body.transaction_id, body.evidence,
            client_id=body.client_id, order_id=body.order_id,
        )

    @r.post("/realize")
    def realize(request: Request, body: RevenueRealizeBody):
        require_control_key(request)
        return lifecycle.realize_revenue(
            body.opportunity_id, client_id=body.client_id,
        )

    @r.get("/status/{opportunity_id}")
    def status(request: Request, opportunity_id: str, client_id: str):
        require_control_key(request)
        row = lifecycle._find(opportunity_id, client_id=client_id)
        if not row:
            return {"ok": False, "status": "NOT_FOUND"}
        data = dict(row.get("data") or {})
        return {
            "ok": True,
            "opportunity_id": opportunity_id,
            "status": data.get("status"),
            "payment_request": data.get("payment_request"),
            "payment_reconciliation": data.get("payment_reconciliation"),
            "revenue_realized": bool(data.get("revenue_realized")),
            "verified_amount_jod": float(data.get("verified_amount_jod", 0) or 0),
        }

    return r
