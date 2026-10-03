"""BRAIN commerce refund/dispute/reversal controls.

This layer records financial reversals as auditable state changes.
It never moves money and never fabricates a refund or dispute outcome.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class EvidenceIn(BaseModel):
    evidence_ref: str = Field(min_length=1, max_length=1000)
    reason: str = Field(default="", max_length=2000)


class ReversalStore:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()

    def _read(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _write(self, data: dict) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def get(self, order_id: str) -> dict | None:
        with self.lock:
            return self._read().get(order_id)

    def apply(self, order_id: str, action: str, body: EvidenceIn) -> dict:
        with self.lock:
            data = self._read()
            order = data.get(order_id)
            if not order:
                raise HTTPException(status_code=404, detail="ORDER_NOT_FOUND")
            if not body.evidence_ref.strip():
                raise HTTPException(status_code=400, detail="EVIDENCE_REQUIRED")

            state = order.get("state")
            payment = order.get("payment", {}).get("status")
            allowed = {
                "PAYMENT_VERIFIED": {"REFUND_REQUESTED", "DISPUTED"},
                "DELIVERY_PENDING": {"DISPUTED"},
                "DELIVERED": {"REFUND_REQUESTED", "DISPUTED"},
                "REVENUE_REALIZED": {"REFUND_REQUESTED", "DISPUTED"},
            }
            target = {
                "refund-request": "REFUND_REQUESTED",
                "dispute-open": "DISPUTED",
            }[action]

            if target not in allowed.get(state, set()):
                raise HTTPException(status_code=409, detail=f"INVALID_REVERSAL:{state}->{target}")

            event = {
                "at": _now(),
                "event": target,
                "evidence_ref": body.evidence_ref.strip(),
                "reason": body.reason.strip(),
            }
            order.setdefault("audit", []).append(event)

            if target == "REFUND_REQUESTED":
                order["refund"] = {
                    "status": "REQUESTED",
                    "evidence_ref": body.evidence_ref.strip(),
                    "reason": body.reason.strip(),
                    "money_movement": False,
                }
            else:
                order["dispute"] = {
                    "status": "OPEN",
                    "evidence_ref": body.evidence_ref.strip(),
                    "reason": body.reason.strip(),
                    "money_movement": False,
                }

            order["updated_at"] = _now()
            data[order_id] = order
            self._write(data)
            return order

    def resolve(self, order_id: str, outcome: str, body: EvidenceIn) -> dict:
        with self.lock:
            data = self._read()
            order = data.get(order_id)
            if not order:
                raise HTTPException(status_code=404, detail="ORDER_NOT_FOUND")
            if not body.evidence_ref.strip():
                raise HTTPException(status_code=400, detail="EVIDENCE_REQUIRED")

            if outcome == "refund-approved":
                if order.get("refund", {}).get("status") != "REQUESTED":
                    raise HTTPException(status_code=409, detail="REFUND_NOT_REQUESTED")
                order["refund"].update({
                    "status": "APPROVED",
                    "resolution_evidence_ref": body.evidence_ref.strip(),
                    "money_movement": False,
                })
                event = "REFUND_APPROVED"
            elif outcome == "refund-rejected":
                if order.get("refund", {}).get("status") != "REQUESTED":
                    raise HTTPException(status_code=409, detail="REFUND_NOT_REQUESTED")
                order["refund"].update({
                    "status": "REJECTED",
                    "resolution_evidence_ref": body.evidence_ref.strip(),
                    "money_movement": False,
                })
                event = "REFUND_REJECTED"
            elif outcome == "dispute-closed":
                if order.get("dispute", {}).get("status") != "OPEN":
                    raise HTTPException(status_code=409, detail="DISPUTE_NOT_OPEN")
                order["dispute"].update({
                    "status": "CLOSED",
                    "resolution_evidence_ref": body.evidence_ref.strip(),
                    "money_movement": False,
                })
                event = "DISPUTE_CLOSED"
            else:
                raise HTTPException(status_code=400, detail="INVALID_OUTCOME")

            order.setdefault("audit", []).append({
                "at": _now(),
                "event": event,
                "evidence_ref": body.evidence_ref.strip(),
                "reason": body.reason.strip(),
            })
            order["updated_at"] = _now()
            data[order_id] = order
            self._write(data)
            return order


def router(data_path: str | None = None) -> APIRouter:
    root = Path(os.getenv("BRAIN_COMMERCE_DB", data_path or "brain_v12_commerce.json"))
    store = ReversalStore(str(root))
    api = APIRouter(prefix="/api/commerce/reversals", tags=["commerce-reversals"])

    def auth(request: Request) -> None:
        from .control_auth import require_control_key
        require_control_key(request)

    @api.post("/{order_id}/refund-request")
    def refund_request(request: Request, order_id: str, body: EvidenceIn):
        auth(request)
        return {"ok": True, "order": store.apply(order_id, "refund-request", body)}

    @api.post("/{order_id}/dispute-open")
    def dispute_open(request: Request, order_id: str, body: EvidenceIn):
        auth(request)
        return {"ok": True, "order": store.apply(order_id, "dispute-open", body)}

    @api.post("/{order_id}/refund-approved")
    def refund_approved(request: Request, order_id: str, body: EvidenceIn):
        auth(request)
        return {"ok": True, "order": store.resolve(order_id, "refund-approved", body)}

    @api.post("/{order_id}/refund-rejected")
    def refund_rejected(request: Request, order_id: str, body: EvidenceIn):
        auth(request)
        return {"ok": True, "order": store.resolve(order_id, "refund-rejected", body)}

    @api.post("/{order_id}/dispute-closed")
    def dispute_closed(request: Request, order_id: str, body: EvidenceIn):
        auth(request)
        return {"ok": True, "order": store.resolve(order_id, "dispute-closed", body)}

    @api.get("/status")
    def status():
        return {"ok": True, "service": "BRAIN Commerce Reversals", "money_movement_enabled": False}

    return api
