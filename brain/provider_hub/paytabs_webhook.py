"""PayTabs webhook/IPN verification helpers."""

from __future__ import annotations

import hashlib
import hmac
import json


def verify_ipn_signature(raw_body: bytes, signature: str, server_key: str) -> bool:
    if not raw_body or not signature or not server_key:
        return False
    expected = hmac.new(server_key.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature.strip().lower())


def parse_and_validate_payment(
    raw_body: bytes,
    signature: str,
    server_key: str,
    *,
    expected_order_id: str,
    expected_amount: str,
    expected_currency: str,
) -> dict:
    if not verify_ipn_signature(raw_body, signature, server_key):
        raise ValueError("INVALID_PAYTABS_SIGNATURE")
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("INVALID_PAYTABS_JSON") from exc

    if str(payload.get("cart_id", "")) != expected_order_id:
        raise ValueError("PAYTABS_ORDER_MISMATCH")

    actual_amount = payload.get("cart_amount")
    if str(actual_amount) != str(expected_amount):
        raise ValueError("PAYTABS_AMOUNT_MISMATCH")

    if str(payload.get("cart_currency", "")) != expected_currency:
        raise ValueError("PAYTABS_CURRENCY_MISMATCH")

    payment_result = payload.get("payment_result") or {}
    if payment_result.get("response_status") != "A":
        raise ValueError("PAYTABS_PAYMENT_NOT_AUTHORISED")

    if not payload.get("tran_ref"):
        raise ValueError("PAYTABS_TRANSACTION_REFERENCE_MISSING")

    return payload
