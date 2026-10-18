"""Safe, public-only Binance Spot API client.

This client deliberately has no API-key support and exposes no account, order,
withdrawal, or transfer endpoints. It is suitable for connectivity and public
market-data checks only. It never places trades or moves funds.
"""
from __future__ import annotations

import json
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class BinanceReadOnlyError(RuntimeError):
    """Raised when a public Binance API request fails or returns invalid data."""


class BinanceReadOnlyClient:
    BASE_URL = "https://api.binance.com"
    _ALLOWED_PATHS = {
        "/api/v3/ping",
        "/api/v3/time",
        "/api/v3/exchangeInfo",
        "/api/v3/ticker/price",
    }

    def __init__(
        self,
        base_url: str = BASE_URL,
        timeout: float = 5.0,
        opener: Callable[..., Any] | None = None,
    ) -> None:
        if not base_url.startswith("https://"):
            raise ValueError("Binance API base URL must use HTTPS")
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._opener = opener or urlopen

    def _get(self, path: str, params: dict[str, str] | None = None) -> Any:
        if path not in self._ALLOWED_PATHS:
            raise ValueError("Endpoint is not on the public read-only allowlist")
        query = f"?{urlencode(params)}" if params else ""
        request = Request(
            f"{self._base_url}{path}{query}",
            headers={"Accept": "application/json", "User-Agent": "ElectronicBrain-ReadOnly/1.0"},
            method="GET",
        )
        try:
            with self._opener(request, timeout=self._timeout) as response:
                status = getattr(response, "status", 200)
                if status < 200 or status >= 300:
                    raise BinanceReadOnlyError(f"Binance returned HTTP {status}")
                payload = response.read()
        except HTTPError as exc:
            raise BinanceReadOnlyError(f"Binance returned HTTP {exc.code}") from None
        except (URLError, TimeoutError, OSError) as exc:
            raise BinanceReadOnlyError(
                f"Binance public API request failed ({type(exc).__name__})"
            ) from None
        try:
            return json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise BinanceReadOnlyError("Binance returned invalid JSON") from None

    def ping(self) -> dict[str, bool]:
        result = self._get("/api/v3/ping")
        if result != {}:
            raise BinanceReadOnlyError("Unexpected ping response")
        return {"connected": True, "read_only": True}

    def server_time(self) -> dict[str, int]:
        result = self._get("/api/v3/time")
        if not isinstance(result, dict) or not isinstance(result.get("serverTime"), int):
            raise BinanceReadOnlyError("Unexpected server-time response")
        return {"serverTime": result["serverTime"]}

    def price(self, symbol: str) -> dict[str, str]:
        symbol = symbol.strip().upper()
        if not symbol or not symbol.isalnum() or len(symbol) > 20:
            raise ValueError("Invalid symbol")
        result = self._get("/api/v3/ticker/price", {"symbol": symbol})
        if (
            not isinstance(result, dict)
            or result.get("symbol") != symbol
            or not isinstance(result.get("price"), str)
        ):
            raise BinanceReadOnlyError("Unexpected ticker response")
        return {"symbol": symbol, "price": result["price"]}

    def exchange_info(self, symbol: str) -> dict[str, Any]:
        symbol = symbol.strip().upper()
        if not symbol or not symbol.isalnum() or len(symbol) > 20:
            raise ValueError("Invalid symbol")
        result = self._get("/api/v3/exchangeInfo", {"symbol": symbol})
        if not isinstance(result, dict) or not isinstance(result.get("symbols"), list):
            raise BinanceReadOnlyError("Unexpected exchange-info response")
        return result
