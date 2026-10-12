"""PayTabs Jordan adapter boundary.

Secrets are read only from environment variables. No credentials are stored
in source control. Network execution is intentionally kept behind a small
client boundary so tests can use a fake transport.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable


DEFAULT_BASE_URL = "https://secure-jordan.paytabs.com"


@dataclass(frozen=True)
class PayTabsConfig:
    profile_id: str
    server_key: str
    base_url: str = DEFAULT_BASE_URL

    @classmethod
    def from_environment(cls) -> "PayTabsConfig":
        profile_id = os.getenv("PAYTABS_PROFILE_ID", "").strip()
        server_key = os.getenv("PAYTABS_SERVER_KEY", "").strip()
        base_url = os.getenv("PAYTABS_BASE_URL", DEFAULT_BASE_URL).strip()
        if not profile_id:
            raise RuntimeError("PAYTABS_PROFILE_ID_MISSING")
        if not server_key:
            raise RuntimeError("PAYTABS_SERVER_KEY_MISSING")
        if "secure-jordan.paytabs.com" not in base_url:
            raise RuntimeError("PAYTABS_BASE_URL_NOT_ALLOWED")
        return cls(profile_id, server_key, base_url.rstrip("/"))


class PayTabsAdapter:
    def __init__(
        self,
        config: PayTabsConfig,
        transport: Callable[[str, dict, dict], dict],
    ) -> None:
        self.config = config
        self.transport = transport

    def create_payment(self, payload: dict) -> dict:
        if not payload.get("cart_id"):
            raise ValueError("CART_ID_REQUIRED")
        if not payload.get("cart_amount"):
            raise ValueError("CART_AMOUNT_REQUIRED")
        if not payload.get("cart_currency"):
            raise ValueError("CART_CURRENCY_REQUIRED")
        headers = {
            "Authorization": self.config.server_key,
            "Content-Type": "application/json",
        }
        return self.transport(
            f"{self.config.base_url}/payment/request",
            {**payload, "profile_id": int(self.config.profile_id)},
            headers,
        )
