"""Industrial Quote & Inquiry Portal for CL-000003.

Bounded MVP: public bilingual inquiry submission plus authenticated admin tracking.
No payment execution and no automatic commercial commitment.
"""
from __future__ import annotations

import json
import os
import secrets
from pathlib import Path
from threading import Lock
from uuid import uuid4
from datetime import datetime, timezone
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

class InquiryIn(BaseModel):
    company: str = Field(min_length=2, max_length=120)
    contact_name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=160)
    phone: str = Field(default="", max_length=40)
    category: str = Field(min_length=2, max_length=120)
    product: str = Field(default="", max_length=160)
    quantity: str = Field(default="", max_length=60)
    message: str = Field(min_length=10, max_length=3000)
    language: str = Field(default="ar", pattern="^(ar|en)$")

class InquiryStore:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = Lock()

    def _load(self) -> list[dict]:
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    def _save(self, items: list[dict]) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, self.path)

    def create(self, body: InquiryIn) -> dict:
        with self.lock:
            items = self._load()
            inquiry = {
                "id": "Q-" + uuid4().hex[:10].upper(),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "status": "NEW",
                "company": body.company.strip(),
                "contact_name": body.contact_name.strip(),
                "email": body.email.strip(),
                "phone": body.phone.strip(),
                "category": body.category.strip(),
                "product": body.product.strip(),
                "quantity": body.quantity.strip(),
                "message": body.message.strip(),
                "language": body.language,
            }
            items.append(inquiry)
            self._save(items)
            return inquiry

    def all(self) -> list[dict]:
        with self.lock:
            return list(reversed(self._load()))

def router(path: str) -> APIRouter:
    store = InquiryStore(path)
    api = APIRouter(prefix="/api/industrial-quotes", tags=["industrial-quotes"])

    def require_admin(key: str | None) -> None:
        configured = os.getenv("BRAIN_CONTROL_KEY", "")
        if not configured or not key or not secrets.compare_digest(key, configured):
            raise HTTPException(status_code=401, detail="control key required")

    @api.get("/health")
    def health():
        return {"ok": True, "service": "Industrial Quote & Inquiry Portal", "version": "1.0"}

    @api.post("/inquiries")
    def create_inquiry(body: InquiryIn):
        item = store.create(body)
        return {
            "ok": True,
            "inquiry_id": item["id"],
            "status": item["status"],
            "created_at": item["created_at"],
            "message": "Inquiry received. No quote or contract has been created.",
        }

    @api.get("/admin/inquiries")
    def admin_inquiries(x_brain_control_key: str | None = Header(default=None)):
        require_admin(x_brain_control_key)
        return {"ok": True, "count": len(store.all()), "items": store.all()}

    return api
