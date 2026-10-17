"""PayTabs webhook/IPN verification helpers."""

from __future__ import annotations

import hashlib
import hmac
import json
from decimal import Decimal, InvalidOperation


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

    try:
        actual_amount = Decimal(str(payload.get("cart_amount"))).quantize(Decimal("0.01"))
        expected_amount_decimal = Decimal(str(expected_amount)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        raise ValueError("PAYTABS_AMOUNT_INVALID") from None
    if not actual_amount.is_finite() or not expected_amount_decimal.is_finite():
        raise ValueError("PAYTABS_AMOUNT_INVALID")
    if actual_amount != expected_amount_decimal:
        raise ValueError("PAYTABS_AMOUNT_MISMATCH")

    if str(payload.get("cart_currency", "")) != expected_currency:
        raise ValueError("PAYTABS_CURRENCY_MISMATCH")

    # PayTabs profiles may place response_status under payment_result or at top level.
    payment_result = payload.get("payment_result") or payload
    if payment_result.get("response_status") != "A":
        raise ValueError("PAYTABS_PAYMENT_NOT_AUTHORISED")
    # Authorization is not captured revenue; require a completed sale.
    if str(payload.get("tran_type", "")).strip().lower() != "sale":
        raise ValueError("PAYTABS_CAPTURED_SALE_REQUIRED")

    if not payload.get("tran_ref"):
        raise ValueError("PAYTABS_TRANSACTION_REFERENCE_MISSING")

    return payload
