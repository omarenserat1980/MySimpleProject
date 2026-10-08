"""BRAIN Digital Commerce API.

Persistent order workflow with fail-closed financial transitions.
This module does not process card data or move money.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import secrets
import hashlib

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

PRODUCTS = [
    {"id": "ai-starter-kit", "name": "BRAIN AI Starter Kit", "price_usd": 9, "type": "digital"},
    {"id": "automation-kit", "name": "BRAIN Automation Kit", "price_usd": 19, "type": "digital"},
    {"id": "business-intelligence-pack", "name": "Business Intelligence Pack", "price_usd": 25, "type": "digital"},
    {"id": "media-toolkit", "name": "BRAIN Media Toolkit", "price_usd": 15, "type": "digital"},
]

STATES = (
    "ORDER_DRAFT",
    "PAYMENT_PENDING",
    "PAYMENT_VERIFIED",
    "DELIVERY_PENDING",
    "DELIVERED",
    "REVENUE_REALIZED",
    "FAILED",
    "REFUNDED",
    "DISPUTED",
)

TERMINAL = {"REVENUE_REALIZED", "FAILED", "REFUNDED", "DISPUTED"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CommerceOrderIn(BaseModel):
    customer_name: str = Field(min_length=1, max_length=160)
    contact: str = Field(min_length=1, max_length=320)
    product_id: str
    details: str = Field(default="", max_length=5000)


class CommerceStateIn(BaseModel):
    evidence_ref: str = Field(min_length=1, max_length=1000)


class PaymentVerificationIn(BaseModel):
    transaction_id: str = Field(min_length=1, max_length=300)
    evidence_ref: str = Field(min_length=1, max_length=1000)


class RevenueRealizationIn(BaseModel):
    delivery_evidence_ref: str = Field(min_length=1, max_length=1000)
    reconciliation_ref: str = Field(min_length=1, max_length=1000)


class CommerceStore:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()

    def _read(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise RuntimeError("COMMERCE_STORE_UNREADABLE") from exc

    def _write(self, data: dict) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def list(self) -> list[dict]:
        with self.lock:
            return list(self._read().values())

    def get(self, order_id: str) -> dict | None:
        with self.lock:
            return self._read().get(order_id)

    def create(self, body: CommerceOrderIn) -> dict:
        product = next((p for p in PRODUCTS if p["id"] == body.product_id), None)
        if not product:
            raise HTTPException(status_code=400, detail="UNKNOWN_PRODUCT")
        order = {
            "order_id": "BRAIN-ORD-" + uuid4().hex[:12].upper(),
            "created_at": _now(),
            "updated_at": _now(),
            "state": "ORDER_DRAFT",
            "customer_name": body.customer_name.strip(),
            "contact": body.contact.strip(),
            "product": product,
            "details": body.details.strip(),
            "payment": {"status": "NOT_CONFIGURED", "evidence_ref": None},
            "delivery": {"status": "NOT_STARTED", "evidence_ref": None},
            "portal": {"token_hash": ""},
            "invoice": {"status": "PENDING_ISSUANCE"},
            "audit": [{"at": _now(), "event": "ORDER_DRAFT_CREATED"}],
        }
        with self.lock:
            data = self._read()
            data[order["order_id"]] = order
            self._write(data)
        return order

    def transition(self, order_id: str, target: str, evidence_ref: str | dict) -> dict:
        if target not in STATES:
            raise HTTPException(status_code=400, detail="INVALID_STATE")
        with self.lock:
            data = self._read()
            order = data.get(order_id)
            if not order:
                raise HTTPException(status_code=404, detail="ORDER_NOT_FOUND")
            current = order["state"]
            if current in TERMINAL:
                raise HTTPException(status_code=409, detail="ORDER_TERMINAL")
            allowed = {
                "ORDER_DRAFT": {"PAYMENT_PENDING", "FAILED"},
                "PAYMENT_PENDING": {"PAYMENT_VERIFIED", "FAILED", "DISPUTED"},
                "PAYMENT_VERIFIED": {"DELIVERY_PENDING", "FAILED", "REFUNDED", "DISPUTED"},
                "DELIVERY_PENDING": {"DELIVERED", "FAILED"},
                "DELIVERED": {"REVENUE_REALIZED"},
            }
            if target not in allowed.get(current, set()):
                raise HTTPException(status_code=409, detail=f"INVALID_TRANSITION:{current}->{target}")
            if target == "PAYMENT_VERIFIED":
                if not isinstance(evidence_ref, dict):
                    raise HTTPException(status_code=400, detail="STRUCTURED_PAYMENT_EVIDENCE_REQUIRED")
                transaction_id = str(evidence_ref.get("transaction_id", "")).strip()
                payment_evidence_ref = str(evidence_ref.get("evidence_ref", "")).strip()
                if not transaction_id or not payment_evidence_ref:
                    raise HTTPException(status_code=400, detail="TRANSACTION_ID_AND_EVIDENCE_REF_REQUIRED")
                payment_record = {
                    "type": "payment_verification",
                    "transaction_id": transaction_id,
                    "evidence_ref": payment_evidence_ref,
                }
                order["payment"] = {"status": "VERIFIED", **payment_record}
                # Only a cryptographically authenticated provider webhook may
                # establish independent commercial authority for revenue.
                if evidence_ref.get("independent_verification") == "SIGNED_PROVIDER_WEBHOOK":
                    order["revenue_authority"] = {
                        "status": "INDEPENDENTLY_VERIFIED",
                        "order_id": order_id,
                        "payment_transaction_id": transaction_id,
                        "provider": str(evidence_ref.get("provider", "")).strip(),
                        "event_id": str(evidence_ref.get("event_id", "")).strip(),
                        "evidence_ref": payment_evidence_ref,
                    }
                order["invoice"] = {"status": "READY", "order_id": order["order_id"], "amount_usd": order["product"]["price_usd"], "payment_evidence_ref": payment_evidence_ref, "transaction_id": transaction_id}
            elif target == "REVENUE_REALIZED":
                if not isinstance(evidence_ref, dict):
                    raise HTTPException(status_code=400, detail="STRUCTURED_RECONCILIATION_EVIDENCE_REQUIRED")
                delivery_ref = str(evidence_ref.get("delivery_evidence_ref", "")).strip()
                reconciliation_ref = str(evidence_ref.get("reconciliation_ref", "")).strip()
                if not delivery_ref or not reconciliation_ref:
                    raise HTTPException(status_code=400, detail="DELIVERY_AND_RECONCILIATION_EVIDENCE_REQUIRED")
                if order.get("payment", {}).get("status") != "VERIFIED":
                    raise HTTPException(status_code=409, detail="PAYMENT_NOT_VERIFIED")
                if order.get("delivery", {}).get("status") != "DELIVERED":
                    raise HTTPException(status_code=409, detail="DELIVERY_NOT_VERIFIED")
                # Revenue realization is owned by an independently verified commercial
                # authority, not by this HTTP endpoint. Local refs alone are insufficient.
                authority = order.get("revenue_authority", {})
                if authority.get("status") != "INDEPENDENTLY_VERIFIED":
                    raise HTTPException(status_code=409, detail="REVENUE_AUTHORITY_REQUIRED")
                if authority.get("order_id") != order_id:
                    raise HTTPException(status_code=409, detail="REVENUE_AUTHORITY_ORDER_MISMATCH")
                if authority.get("payment_transaction_id") != order.get("payment", {}).get("transaction_id"):
                    raise HTTPException(status_code=409, detail="REVENUE_AUTHORITY_PAYMENT_MISMATCH")
                order["revenue"] = {"status": "REALIZED", "delivery_evidence_ref": delivery_ref, "reconciliation_ref": reconciliation_ref, "authority_ref": authority.get("evidence_ref")}
            elif target == "DELIVERED":
                order["delivery"] = {"status": "DELIVERED", "evidence_ref": evidence_ref.strip()}
            order["state"] = target
            order["updated_at"] = _now()
            audit_evidence = evidence_ref if isinstance(evidence_ref, dict) else evidence_ref.strip()
            order["audit"].append({"at": _now(), "event": target, "evidence": audit_evidence})
            data[order_id] = order
            self._write(data)
            return order


def router(data_path: str | None = None) -> APIRouter:
    root = Path(os.getenv("BRAIN_COMMERCE_DB", data_path or "brain_v12_commerce.json"))
    store = CommerceStore(str(root))
    api = APIRouter(prefix="/api/commerce", tags=["commerce"])

    @api.get("/catalog")
    def catalog():
        return {"ok": True, "currency": "USD", "products": PRODUCTS}

    @api.post("/orders")
    def create_order(body: CommerceOrderIn):
        order = store.create(body)
        portal_token = secrets.token_urlsafe(32)
        order["portal"]["token_hash"] = hashlib.sha256(portal_token.encode()).hexdigest()
        data = {x["order_id"]: x for x in store.list()}
        data[order["order_id"]] = order
        store._write(data)
        return {"ok": True, "order": order, "portal_token": portal_token, "portal_path": "/api/customer/orders/" + portal_token}

    @api.get("/orders")
    def list_orders(request: Request):
        from .control_auth import require_control_key
        require_control_key(request)
        return {"ok": True, "orders": store.list()}

    @api.get("/orders/{order_id}")
    def get_order(request: Request, order_id: str):
        from .control_auth import require_control_key
        require_control_key(request)
        order = store.get(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="ORDER_NOT_FOUND")
        return {"ok": True, "order": order}

    @api.post("/orders/{order_id}/payment-pending")
    def payment_pending(order_id: str, body: CommerceStateIn):
        return {"ok": True, "order": store.transition(order_id, "PAYMENT_PENDING", body.evidence_ref)}

    @api.post("/orders/{order_id}/payment-verified")
    def payment_verified(request: Request, order_id: str, body: PaymentVerificationIn):
        from .control_auth import require_control_key
        require_control_key(request)
        return {"ok": True, "order": store.transition(order_id, "PAYMENT_VERIFIED", body.dict())}

    @api.post("/orders/{order_id}/delivery-pending")
    def delivery_pending(request: Request, order_id: str, body: CommerceStateIn):
        from .control_auth import require_control_key
        require_control_key(request)
        return {"ok": True, "order": store.transition(order_id, "DELIVERY_PENDING", body.evidence_ref)}

    @api.post("/orders/{order_id}/delivered")
    def delivered(request: Request, order_id: str, body: CommerceStateIn):
        from .control_auth import require_control_key
        require_control_key(request)
        return {"ok": True, "order": store.transition(order_id, "DELIVERED", body.evidence_ref)}

    @api.post("/orders/{order_id}/revenue-realized")
    def revenue_realized(request: Request, order_id: str, body: RevenueRealizationIn):
        from .control_auth import require_control_key
        require_control_key(request)
        return {"ok": True, "order": store.transition(order_id, "REVENUE_REALIZED", body.dict())}

    @api.get("/status")
    def status():
        orders = store.list()
        counts = {s: sum(1 for o in orders if o.get("state") == s) for s in STATES}
        return {
            "ok": True,
            "service": "BRAIN Digital Commerce",
            "live_payment_provider": False,
            "revenue_claimed": sum(counts[s] for s in ("REVENUE_REALIZED",)),
            "order_counts": counts,
        }

    return api
