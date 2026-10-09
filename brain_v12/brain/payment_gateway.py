"""Fail-closed payment provider adapter and webhook verification.

This module defines a provider-neutral contract. It does not call a bank,
PSP, wallet, or card network. Providers can implement the contract later.
Webhook processing verifies an HMAC signature, timestamp freshness, and an
event-id replay cache before allowing an auditable payment state transition.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
import tempfile
import time
from pathlib import Path
from typing import Protocol

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from .commerce_api import CommerceStore


class PaymentIntent(BaseModel):
    order_id: str
    amount_usd: float
    currency: str = "USD"
    provider: str = "UNCONFIGURED"


class PaymentProvider(Protocol):
    name: str
    def create_payment_intent(self, intent: PaymentIntent) -> dict: ...


class DisabledPaymentProvider:
    name = "UNCONFIGURED"
    def create_payment_intent(self, intent: PaymentIntent) -> dict:
        raise RuntimeError("PAYMENT_PROVIDER_NOT_CONFIGURED")


class PaymentEventJournal:
    """Durable payment-event state machine for crash recovery."""
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
            raise RuntimeError("PAYMENT_EVENT_JOURNAL_UNREADABLE") from exc

    def _write(self, data: dict) -> None:
        payload = json.dumps(data, indent=2)
        fd, tmp_name = tempfile.mkstemp(
            prefix=self.path.name + ".",
            suffix=".tmp",
            dir=str(self.path.parent),
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, self.path)
            try:
                dir_fd = os.open(self.path.parent, os.O_RDONLY)
                try:
                    os.fsync(dir_fd)
                finally:
                    os.close(dir_fd)
            except OSError:
                pass
        except OSError as exc:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise RuntimeError("PAYMENT_EVENT_JOURNAL_WRITE_FAILED") from exc

    def get(self, event_id: str) -> dict | None:
        with self.lock:
            return self._read().get(event_id)

    def begin(self, payload: "WebhookEnvelope") -> dict:
        fingerprint = hashlib.sha256(
            json.dumps(payload.model_dump(), sort_keys=True).encode("utf-8")
        ).hexdigest()
        with self.lock:
            data = self._read()
            existing = data.get(payload.event_id)
            if existing:
                if existing.get("fingerprint") != fingerprint:
                    raise RuntimeError("PAYMENT_EVENT_ID_CONFLICT")
                return existing
            record = {
                "state": "AUTHENTICATED",
                "fingerprint": fingerprint,
                "order_id": payload.order_id,
                "provider": payload.provider,
                "payment_reference": payload.payment_reference,
                "created_at": int(time.time()),
            }
            data[payload.event_id] = record
            self._write(data)
            return record

    def mark(self, event_id: str, state: str) -> None:
        with self.lock:
            data = self._read()
            record = data.get(event_id)
            if not record:
                raise RuntimeError("PAYMENT_EVENT_JOURNAL_ENTRY_MISSING")
            record["state"] = state
            record["updated_at"] = int(time.time())
            data[event_id] = record
            self._write(data)


class WebhookStore:
    def __init__(self, path: str):
        self.path = Path(path)
        self.lock = threading.RLock()
    def _read(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise RuntimeError("WEBHOOK_REPLAY_STORE_UNREADABLE") from exc
    def seen(self, event_id: str) -> bool:
        with self.lock:
            return event_id in self._read()
    def record(self, event_id: str, payment_reference: str | None = None, order_id: str | None = None) -> None:
        with self.lock:
            data = self._read()
            data[event_id] = {
                "seen_at": int(time.time()),
                "payment_reference": payment_reference,
                "order_id": order_id,
            }
            payload = json.dumps(data, indent=2)
            fd, tmp_name = tempfile.mkstemp(
                prefix=self.path.name + ".",
                suffix=".tmp",
                dir=str(self.path.parent),
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    handle.write(payload)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(tmp_name, self.path)
                try:
                    dir_fd = os.open(self.path.parent, os.O_RDONLY)
                    try:
                        os.fsync(dir_fd)
                    finally:
                        os.close(dir_fd)
                except OSError:
                    pass
            except OSError as exc:
                try:
                    os.unlink(tmp_name)
                except OSError:
                    pass
                raise RuntimeError("WEBHOOK_REPLAY_STORE_WRITE_FAILED") from exc

    def payment_seen(self, payment_reference: str) -> bool:
        with self.lock:
            return any(
                isinstance(v, dict) and v.get("payment_reference") == payment_reference
                for v in self._read().values()
            )


class WebhookEnvelope(BaseModel):
    event_id: str = Field(min_length=8, max_length=200)
    event_type: str = Field(min_length=1, max_length=100)
    order_id: str = Field(min_length=1, max_length=100)
    provider: str = Field(min_length=1, max_length=100)
    payment_reference: str = Field(min_length=1, max_length=300)
    amount_usd: float = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    timestamp: int


def signature(secret: str, timestamp: int, raw_body: bytes) -> str:
    payload = f"{timestamp}.".encode() + raw_body
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def router(data_path: str, replay_path: str | None = None) -> APIRouter:
    store = CommerceStore(data_path)
    replay = WebhookStore(replay_path or data_path + ".webhooks.json")
    journal = PaymentEventJournal(data_path + ".payment-events.json")
    api = APIRouter(prefix="/api/payments", tags=["payments"])

    @api.post("/intent")
    def create_intent(request: Request, order_id: str):
        from .control_auth import require_control_key
        require_control_key(request)
        order = store.get(order_id)
        if not order:
            raise HTTPException(404, "ORDER_NOT_FOUND")
        return {"ok": False, "configured": False, "provider": "UNCONFIGURED", "detail": "PAYMENT_PROVIDER_NOT_CONFIGURED"}

    @api.post("/webhook")
    async def webhook(request: Request):
        secret = os.getenv("BRAIN_PAYMENT_WEBHOOK_SECRET", "")
        if not secret:
            raise HTTPException(503, "PAYMENT_WEBHOOK_NOT_CONFIGURED")
        raw = await request.body()
        supplied = request.headers.get("X-Brain-Payment-Signature", "")
        timestamp_header = request.headers.get("X-Brain-Payment-Timestamp", "")
        if not supplied or not timestamp_header:
            raise HTTPException(401, "WEBHOOK_SIGNATURE_REQUIRED")
        try:
            timestamp = int(timestamp_header)
        except ValueError:
            raise HTTPException(400, "INVALID_WEBHOOK_TIMESTAMP")
        if abs(int(time.time()) - timestamp) > 300:
            raise HTTPException(401, "WEBHOOK_TIMESTAMP_EXPIRED")
        expected = signature(secret, timestamp, raw)
        if not hmac.compare_digest(supplied, expected):
            raise HTTPException(401, "INVALID_WEBHOOK_SIGNATURE")
        try:
            # Support both Pydantic v1 (parse_raw) and v2 (model_validate_json).
            # Some supported self-hosted runners still resolve Pydantic v1.
            validate_json = getattr(WebhookEnvelope, "model_validate_json", None)
            if callable(validate_json):
                payload = validate_json(raw)
            else:
                payload = WebhookEnvelope.parse_raw(raw)
        except Exception:
            raise HTTPException(400, "INVALID_WEBHOOK_PAYLOAD")
        with replay.lock:
            journal_entry = journal.get(payload.event_id)
            if journal_entry and journal_entry.get("state") == "COMMERCE_COMMITTED":
                # Recovery is valid only when the durable commerce commit matches
                # this authenticated payment. The journal state alone is insufficient.
                recovered_order = store.get(payload.order_id)
                if not recovered_order:
                    raise HTTPException(404, "ORDER_NOT_FOUND")
                recovered_payment = recovered_order.get("payment", {})
                recovered_authority = recovered_order.get("revenue_authority", {})
                if recovered_order.get("state") != "PAYMENT_VERIFIED":
                    raise HTTPException(409, "JOURNAL_COMMERCE_STATE_MISMATCH")
                if recovered_payment.get("transaction_id") != payload.payment_reference:
                    raise HTTPException(409, "JOURNAL_PAYMENT_REFERENCE_MISMATCH")
                if recovered_authority.get("provider") != payload.provider:
                    raise HTTPException(409, "JOURNAL_PROVIDER_MISMATCH")
                if recovered_authority.get("event_id") != payload.event_id:
                    raise HTTPException(409, "JOURNAL_EVENT_ID_MISMATCH")
                replay.record(payload.event_id, payload.payment_reference, payload.order_id)
                journal.mark(payload.event_id, "COMPLETED")
                return {"ok": True, "verified": True, "idempotent": True,
                        "order_id": payload.order_id, "state": "PAYMENT_VERIFIED",
                        "payment_reference": payload.payment_reference}
            if journal_entry and journal_entry.get("state") == "COMPLETED":
                raise HTTPException(409, "WEBHOOK_REPLAY")
            if replay.seen(payload.event_id):
                raise HTTPException(409, "WEBHOOK_REPLAY")
            if replay.payment_seen(payload.payment_reference):
                raise HTTPException(409, "PAYMENT_REFERENCE_REPLAY")
            configured_provider = os.getenv("BRAIN_PAYMENT_PROVIDER", "").strip()
            if not configured_provider:
                raise HTTPException(503, "PAYMENT_PROVIDER_NOT_CONFIGURED")
            if payload.provider != configured_provider:
                raise HTTPException(409, "PAYMENT_PROVIDER_MISMATCH")
            if payload.event_type != "payment.verified":
                replay.record(payload.event_id, payload.payment_reference, payload.order_id)
                return {"ok": True, "ignored": True, "event_id": payload.event_id}
            order = store.get(payload.order_id)
            if not order:
                raise HTTPException(404, "ORDER_NOT_FOUND")
            if payload.currency.upper() != "USD":
                raise HTTPException(409, "CURRENCY_MISMATCH")
            expected_amount = float(order["product"]["price_usd"])
            if abs(payload.amount_usd - expected_amount) > 0.000001:
                raise HTTPException(409, "AMOUNT_MISMATCH")
            journal_entry = journal.begin(payload)
            if journal_entry.get("state") == "COMMERCE_COMMITTED":
                replay.record(payload.event_id, payload.payment_reference, payload.order_id)
                journal.mark(payload.event_id, "COMPLETED")
                return {"ok": True, "verified": True, "idempotent": True,
                        "order_id": payload.order_id, "state": "PAYMENT_VERIFIED",
                        "payment_reference": payload.payment_reference}

            if order.get("state") == "PAYMENT_VERIFIED":
                existing_tx = str(order.get("payment", {}).get("transaction_id", "")).strip()
                existing_provider = str(order.get("revenue_authority", {}).get("provider", "")).strip()
                existing_event = str(order.get("revenue_authority", {}).get("event_id", "")).strip()
                if existing_tx == payload.payment_reference and existing_provider == payload.provider:
                    # Same payment may be retried with a new delivery event id by the
                    # provider; preserve the original authoritative event identity.
                    replay.record(payload.event_id, payload.payment_reference, payload.order_id)
                    return {"ok": True, "verified": True, "idempotent": True,
                            "order_id": order["order_id"], "state": order["state"],
                            "payment_reference": payload.payment_reference,
                            "authoritative_event_id": existing_event}
                raise HTTPException(409, "PAYMENT_REFERENCE_ORDER_CONFLICT")
            if order.get("state") != "PAYMENT_PENDING":
                raise HTTPException(409, "INVALID_PAYMENT_STATE")
            order = store.transition(payload.order_id, "PAYMENT_VERIFIED", {
            "transaction_id": payload.payment_reference,
            "evidence_ref": f"payment-webhook:{payload.provider}:{payload.event_id}",
            "provider": payload.provider,
            "event_id": payload.event_id,
            "verified_at": int(time.time()),
            "independent_verification": "SIGNED_PROVIDER_WEBHOOK",
            })
            journal.mark(payload.event_id, "COMMERCE_COMMITTED")
            replay.record(payload.event_id, payload.payment_reference, payload.order_id)
            journal.mark(payload.event_id, "COMPLETED")
            return {"ok": True, "verified": True, "order_id": order["order_id"], "state": order["state"], "payment_reference": payload.payment_reference}

    return api
