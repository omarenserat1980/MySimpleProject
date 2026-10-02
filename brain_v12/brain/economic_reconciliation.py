"""Commerce-to-economic-ledger reconciliation gate.

No money is moved by this module. It only records a verified financial
transition after independent payment and delivery evidence are supplied.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel


class ReconciliationRequest(BaseModel):
    order_id: str
    payment_evidence_ref: str
    delivery_evidence_ref: str
    amount_usd: float
    currency: str = "USD"


class ReconciliationStore:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {"version": 1, "records": {}}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, data: Dict[str, Any]) -> None:
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(tmp, self.path)

    def reconcile(self, body: ReconciliationRequest) -> Dict[str, Any]:
        if not body.payment_evidence_ref.strip() or not body.delivery_evidence_ref.strip():
            raise ValueError("independent payment and delivery evidence are required")
        if body.currency != "USD" or body.amount_usd <= 0:
            raise ValueError("unsupported currency or invalid amount")

        data = self._load()
        if body.order_id in data["records"]:
            return data["records"][body.order_id]

        record = {
            "order_id": body.order_id,
            "state": "REVENUE_REALIZED",
            "amount_usd": body.amount_usd,
            "currency": body.currency,
            "payment_evidence_ref": body.payment_evidence_ref,
            "delivery_evidence_ref": body.delivery_evidence_ref,
            "money_movement": False,
            "audit_fingerprint": hashlib.sha256(
                json.dumps(body.model_dump(), sort_keys=True).encode("utf-8")
            ).hexdigest(),
        }
        data["records"][body.order_id] = record
        self._save(data)
        return record


def router(path: str) -> APIRouter:
    store = ReconciliationStore(path)
    api = APIRouter(prefix="/api/economic-reconciliation", tags=["economic-reconciliation"])

    @api.get("/status")
    def status() -> Dict[str, Any]:
        return {
            "service": "BRAIN Economic Reconciliation",
            "money_movement_enabled": False,
            "records": len(store._load()["records"]),
        }

    @api.post("/reconcile")
    def reconcile(
        body: ReconciliationRequest,
        x_brain_control_key: Optional[str] = Header(default=None),
    ) -> Dict[str, Any]:
        configured = os.getenv("BRAIN_CONTROL_KEY", "")
        if not configured or not x_brain_control_key or not hmac.compare_digest(
            x_brain_control_key, configured
        ):
            raise HTTPException(status_code=401, detail="control key required")
        try:
            return store.reconcile(body)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return api
