"""BRAIN customer portal and invoice/delivery layer."""
from __future__ import annotations
import hashlib, hmac, os
from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from .commerce_api import CommerceStore

class DeliveryGrantIn(BaseModel):
    resource_ref: str = Field(min_length=1, max_length=2000)
    evidence_ref: str = Field(min_length=1, max_length=1000)

def router(data_path: str | None = None) -> APIRouter:
    store = CommerceStore(str(Path(os.getenv("BRAIN_COMMERCE_DB", data_path or "brain_v12_commerce.json"))))
    api = APIRouter(prefix="/api/customer", tags=["customer-portal"])
    def token_hash(value: str) -> str:
        return hashlib.sha256(value.encode()).hexdigest()
    def lookup(value: str):
        if len(value) < 32: raise HTTPException(401, "INVALID_PORTAL_TOKEN")
        wanted = token_hash(value)
        for order in store.list():
            if hmac.compare_digest(order.get("portal", {}).get("token_hash", ""), wanted):
                return order
        raise HTTPException(404, "PORTAL_NOT_FOUND")
    def save(order):
        data={x["order_id"]:x for x in store.list()}
        data[order["order_id"]]=order
        store._write(data)
    @api.get("/orders/{portal_token}")
    def portal_order(portal_token: str):
        o=lookup(portal_token)
        return {"ok":True,"portal":{"order_id":o["order_id"],"state":o["state"],"created_at":o["created_at"],"product":o["product"],"customer_name":o["customer_name"],"payment_status":o.get("payment",{}).get("status"),"delivery_status":o.get("delivery",{}).get("status"),"invoice":o.get("invoice")}}
    @api.get("/orders/{portal_token}/invoice")
    def invoice(portal_token: str):
        o=lookup(portal_token)
        if o["state"] in {"ORDER_DRAFT","PAYMENT_PENDING"}: raise HTTPException(409,"INVOICE_NOT_READY")
        return {"ok":True,"invoice":o.get("invoice",{"status":"PENDING_ISSUANCE","order_id":o["order_id"],"amount_usd":o["product"]["price_usd"]})}
    @api.post("/orders/{order_id}/delivery-grant")
    def delivery_grant(order_id: str, body: DeliveryGrantIn):
        o=store.get(order_id)
        if not o: raise HTTPException(404,"ORDER_NOT_FOUND")
        if o.get("state")!="PAYMENT_VERIFIED": raise HTTPException(409,"PAYMENT_MUST_BE_VERIFIED")
        o["delivery"]={"status":"DELIVERED","resource_ref":body.resource_ref,"evidence_ref":body.evidence_ref,"grant_id":"BRAIN-GRANT-"+uuid4().hex[:12].upper()}
        o["state"]="DELIVERED"
        o.setdefault("audit",[]).append({"event":"DELIVERY_GRANTED","evidence_ref":body.evidence_ref})
        save(o)
        return {"ok":True,"order_id":order_id,"delivery":o["delivery"]}
    return api
