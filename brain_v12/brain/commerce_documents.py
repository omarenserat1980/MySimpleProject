"""BRAIN commerce invoice and receipt artifacts.

Documents are evidence-backed representations of the order state. They do not
move money, charge customers, or claim revenue by themselves.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request

from .commerce_api import CommerceStore


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fingerprint(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def _invoice(order: dict) -> dict:
    if order.get("state") in {"ORDER_DRAFT", "PAYMENT_PENDING"}:
        raise HTTPException(409, "INVOICE_NOT_READY")
    payment_ref = order.get("payment", {}).get("evidence_ref")
    if not payment_ref:
        raise HTTPException(409, "PAYMENT_EVIDENCE_REQUIRED")
    body = {
        "document_type": "INVOICE",
        "invoice_id": "BRAIN-INV-" + order["order_id"].removeprefix("BRAIN-ORD-"),
        "order_id": order["order_id"],
        "issued_at": order.get("updated_at") or _now(),
        "currency": "USD",
        "amount_usd": order["product"]["price_usd"],
        "customer_name": order["customer_name"],
        "contact": order["contact"],
        "product_id": order["product"]["id"],
        "product_name": order["product"]["name"],
        "payment_evidence_ref": payment_ref,
        "status": "ISSUED",
    }
    body["document_fingerprint"] = _fingerprint(body)
    return body


def _receipt(order: dict) -> dict:
    if order.get("payment", {}).get("status") != "VERIFIED":
        raise HTTPException(409, "PAYMENT_NOT_VERIFIED")
    payment_ref = order.get("payment", {}).get("evidence_ref")
    if not payment_ref:
        raise HTTPException(409, "PAYMENT_EVIDENCE_REQUIRED")
    body = {
        "document_type": "PAYMENT_RECEIPT",
        "receipt_id": "BRAIN-RCP-" + order["order_id"].removeprefix("BRAIN-ORD-"),
        "order_id": order["order_id"],
        "issued_at": order.get("updated_at") or _now(),
        "currency": "USD",
        "amount_usd": order["product"]["price_usd"],
        "customer_name": order["customer_name"],
        "contact": order["contact"],
        "product_id": order["product"]["id"],
        "product_name": order["product"]["name"],
        "payment_evidence_ref": payment_ref,
        "status": "PAYMENT_VERIFIED",
    }
    body["document_fingerprint"] = _fingerprint(body)
    return body


def router(data_path: str | None = None) -> APIRouter:
    store = CommerceStore(data_path)
    api = APIRouter(prefix="/api/commerce/documents", tags=["commerce-documents"])

    @api.get("/orders/{order_id}/invoice")
    def invoice(request: Request, order_id: str):
        from .control_auth import require_control_key
        require_control_key(request)
        order = store.get(order_id)
        if not order:
            raise HTTPException(404, "ORDER_NOT_FOUND")
        return {"ok": True, "invoice": _invoice(order)}

    @api.get("/orders/{order_id}/receipt")
    def receipt(request: Request, order_id: str):
        from .control_auth import require_control_key
        require_control_key(request)
        order = store.get(order_id)
        if not order:
            raise HTTPException(404, "ORDER_NOT_FOUND")
        return {"ok": True, "receipt": _receipt(order)}

    return api
