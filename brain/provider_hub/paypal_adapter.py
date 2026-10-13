"""PayPal Orders API adapter with an injectable transport for safe testing.

Only Sandbox is allowed by default. Credentials are read from environment
variables and must never be logged or committed.
"""
from __future__ import annotations

import base64
import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote, urlsplit
from urllib.request import Request, urlopen
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Callable

Transport = Callable[[str, str, dict, dict | None], dict]
DEFAULT_BASE_URL = "https://api-m.sandbox.paypal.com"


@dataclass(frozen=True)
class PayPalConfig:
    client_id: str
    client_secret: str
    base_url: str = DEFAULT_BASE_URL

    @classmethod
    def from_environment(cls) -> "PayPalConfig":
        client_id = os.getenv("PAYPAL_CLIENT_ID", "").strip()
        client_secret = os.getenv("PAYPAL_CLIENT_SECRET", "").strip()
        base_url = os.getenv("PAYPAL_BASE_URL", DEFAULT_BASE_URL).strip().rstrip("/")
        if not client_id:
            raise RuntimeError("PAYPAL_CLIENT_ID_MISSING")
        if not client_secret:
            raise RuntimeError("PAYPAL_CLIENT_SECRET_MISSING")
        if base_url != DEFAULT_BASE_URL:
            raise RuntimeError("PAYPAL_BASE_URL_NOT_ALLOWED")
        return cls(client_id, client_secret, base_url)


def http_transport(url: str, method: str, headers: dict, payload: dict | None) -> dict:
    """Perform one PayPal HTTPS request; never log credentials or response bodies."""
    content_type = headers.get("Content-Type", "")
    if content_type == "application/x-www-form-urlencoded":
        body = urlencode(payload or {}).encode("ascii")
    else:
        body = json.dumps(payload or {}).encode("utf-8")
    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=20) as response:
            raw = response.read()
    except HTTPError as exc:
        raise RuntimeError(f"PAYPAL_HTTP_ERROR_{exc.code}") from None
    except (URLError, TimeoutError, OSError):
        raise RuntimeError("PAYPAL_NETWORK_ERROR") from None
    try:
        decoded = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise RuntimeError("PAYPAL_INVALID_JSON_RESPONSE") from None
    if not isinstance(decoded, dict):
        raise RuntimeError("PAYPAL_INVALID_RESPONSE")
    return decoded


class PayPalAdapter:
    def __init__(self, config: PayPalConfig, transport: Transport | None = None) -> None:
        self.config = config
        self.transport = transport or http_transport

    @staticmethod
    def _valid_amount(amount: str) -> str:
        try:
            value = Decimal(str(amount))
        except (InvalidOperation, ValueError):
            raise ValueError("INVALID_AMOUNT") from None
        if not value.is_finite() or value <= 0 or value.as_tuple().exponent < -2:
            raise ValueError("INVALID_AMOUNT")
        return format(value.quantize(Decimal("0.01")), "f")

    def _access_token(self) -> str:
        credentials = f"{self.config.client_id}:{self.config.client_secret}".encode()
        basic = base64.b64encode(credentials).decode("ascii")
        result = self.transport(
            f"{self.config.base_url}/v1/oauth2/token",
            "POST",
            {"Authorization": f"Basic {basic}",
             "Content-Type": "application/x-www-form-urlencoded"},
            {"grant_type": "client_credentials"},
        )
        token = result.get("access_token")
        if not token:
            raise RuntimeError("PAYPAL_ACCESS_TOKEN_MISSING")
        return str(token)

    def create_order(self, *, order_id: str, amount: str, currency: str,
                     return_url: str, cancel_url: str) -> dict:
        if not order_id.strip() or len(order_id) > 127:
            raise ValueError("ORDER_ID_REQUIRED_OR_TOO_LONG")
        normalized_amount = self._valid_amount(amount)
        currency = currency.strip().upper()
        if len(currency) != 3 or not currency.isalpha():
            raise ValueError("INVALID_CURRENCY")
        for candidate in (return_url, cancel_url):
            parsed = urlsplit(candidate)
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
                raise ValueError("HTTPS_RETURN_URLS_REQUIRED")
        token = self._access_token()
        return self.transport(
            f"{self.config.base_url}/v2/checkout/orders",
            "POST",
            {"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            {"intent": "CAPTURE", "purchase_units": [{
                "reference_id": order_id,
                "invoice_id": order_id,
                "amount": {"currency_code": currency, "value": normalized_amount},
            }], "application_context": {
                "return_url": return_url, "cancel_url": cancel_url,
            }},
        )

    def capture_order(self, *, paypal_order_id: str) -> dict:
        if not paypal_order_id.strip():
            raise ValueError("PAYPAL_ORDER_ID_REQUIRED")
        token = self._access_token()
        return self.transport(
            f"{self.config.base_url}/v2/checkout/orders/{quote(paypal_order_id, safe='')}/capture",
            "POST",
            {"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            {},
        )

    def verify_webhook_event(self, *, webhook_id: str, headers: dict,
                             event: dict) -> dict:
        """Ask PayPal to verify a received webhook; callers must pass the raw event
        parsed as JSON and the exact PayPal transmission headers.
        """
        if not webhook_id.strip():
            raise ValueError("PAYPAL_WEBHOOK_ID_REQUIRED")
        required = {
            "auth_algo": headers.get("PAYPAL-AUTH-ALGO") or headers.get("paypal-auth-algo"),
            "cert_url": headers.get("PAYPAL-CERT-URL") or headers.get("paypal-cert-url"),
            "transmission_id": headers.get("PAYPAL-TRANSMISSION-ID") or headers.get("paypal-transmission-id"),
            "transmission_sig": headers.get("PAYPAL-TRANSMISSION-SIG") or headers.get("paypal-transmission-sig"),
            "transmission_time": headers.get("PAYPAL-TRANSMISSION-TIME") or headers.get("paypal-transmission-time"),
        }
        if not all(isinstance(value, str) and value.strip() for value in required.values()):
            raise ValueError("PAYPAL_WEBHOOK_HEADERS_MISSING")
        if not isinstance(event, dict) or not event.get("id") or not event.get("event_type"):
            raise ValueError("PAYPAL_WEBHOOK_EVENT_INVALID")
        token = self._access_token()
        result = self.transport(
            f"{self.config.base_url}/v1/notifications/verify-webhook-signature",
            "POST",
            {"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            {**required, "webhook_id": webhook_id, "webhook_event": event},
        )
        if result.get("verification_status") != "SUCCESS":
            raise ValueError("PAYPAL_WEBHOOK_SIGNATURE_INVALID")
        return result
