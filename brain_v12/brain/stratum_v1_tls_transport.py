"""TLS-only Stratum V1 line transport, fail-closed by default.

The transport is deliberately not instantiated or connected by API endpoints.
Callers must pass explicit approval and endpoint verification to connect().
No credentials or payload contents are logged. Unit tests inject a fake socket.
"""
from __future__ import annotations

import json
import socket
import ssl
from typing import Any, Callable

from .stratum_v1_adapter_contract import validate_endpoint

MAX_LINE_BYTES = 64 * 1024


class StratumTransportError(RuntimeError):
    """Safe transport error; messages never include payloads or credentials."""


class StratumV1TLSTransport:
    def __init__(
        self,
        host: str,
        port: int,
        *,
        timeout_seconds: float = 5.0,
        max_line_bytes: int = MAX_LINE_BYTES,
        socket_factory: Callable[..., Any] | None = None,
        ssl_context: ssl.SSLContext | None = None,
    ) -> None:
        validate_endpoint(host, port, tls=True)
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or not 0.1 <= timeout_seconds <= 30:
            raise ValueError("STRATUM_TIMEOUT_OUT_OF_RANGE")
        if isinstance(max_line_bytes, bool) or not isinstance(max_line_bytes, int) or not 256 <= max_line_bytes <= MAX_LINE_BYTES:
            raise ValueError("STRATUM_LINE_LIMIT_OUT_OF_RANGE")
        self.host = host.strip()
        self.port = port
        self.timeout_seconds = float(timeout_seconds)
        self.max_line_bytes = max_line_bytes
        self._socket_factory = socket_factory or socket.create_connection
        self._ssl_context = ssl_context or ssl.create_default_context()
        self._sock: Any = None
        self._buffer = bytearray()

    @property
    def connected(self) -> bool:
        return self._sock is not None

    def connect(self, *, explicit_approval: bool, endpoint_verified: bool) -> None:
        """Open TLS transport only after caller supplies both independent gates."""
        if explicit_approval is not True:
            raise StratumTransportError("EXPLICIT_USER_APPROVAL_REQUIRED")
        if endpoint_verified is not True:
            raise StratumTransportError("POOL_ENDPOINT_VERIFICATION_REQUIRED")
        if self._sock is not None:
            raise StratumTransportError("TRANSPORT_ALREADY_CONNECTED")
        raw = None
        try:
            raw = self._socket_factory((self.host, self.port), timeout=self.timeout_seconds)
            wrapped = self._ssl_context.wrap_socket(raw, server_hostname=self.host)
            wrapped.settimeout(self.timeout_seconds)
            self._sock = wrapped
        except (OSError, ssl.SSLError, TimeoutError) as exc:
            if raw is not None:
                try:
                    raw.close()
                except Exception:
                    pass
            # Avoid embedding exception text: TLS/socket errors can contain endpoints.
            raise StratumTransportError("TLS_CONNECTION_FAILED") from exc

    def send_message(self, message: dict[str, Any]) -> None:
        if self._sock is None:
            raise StratumTransportError("TRANSPORT_NOT_CONNECTED")
        if not isinstance(message, dict):
            raise ValueError("STRATUM_MESSAGE_MUST_BE_OBJECT")
        try:
            payload = json.dumps(message, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8") + b"\n"
        except (TypeError, ValueError) as exc:
            raise ValueError("INVALID_STRATUM_JSON_MESSAGE") from exc
        if len(payload) > self.max_line_bytes:
            raise StratumTransportError("OUTBOUND_LINE_TOO_LARGE")
        try:
            self._sock.sendall(payload)
        except (OSError, TimeoutError) as exc:
            self.close()
            raise StratumTransportError("STRATUM_SEND_FAILED") from exc

    def receive_message(self) -> dict[str, Any]:
        if self._sock is None:
            raise StratumTransportError("TRANSPORT_NOT_CONNECTED")
        try:
            while True:
                newline = self._buffer.find(b"\n")
                if newline >= 0:
                    raw = bytes(self._buffer[:newline])
                    del self._buffer[:newline + 1]
                    if not raw:
                        continue
                    break
                if len(self._buffer) >= self.max_line_bytes:
                    self.close()
                    raise StratumTransportError("INBOUND_LINE_TOO_LARGE")
                chunk = self._sock.recv(min(4096, self.max_line_bytes - len(self._buffer)))
                if not chunk:
                    self.close()
                    raise StratumTransportError("STRATUM_CONNECTION_CLOSED")
                self._buffer.extend(chunk)
                if len(self._buffer) > self.max_line_bytes:
                    self.close()
                    raise StratumTransportError("INBOUND_LINE_TOO_LARGE")
        except (OSError, TimeoutError) as exc:
            self.close()
            raise StratumTransportError("STRATUM_RECEIVE_FAILED") from exc
        try:
            message = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise StratumTransportError("INVALID_STRATUM_JSON") from exc
        if not isinstance(message, dict):
            raise StratumTransportError("STRATUM_MESSAGE_MUST_BE_OBJECT")
        return message

    def close(self) -> None:
        sock, self._sock = self._sock, None
        self._buffer.clear()
        if sock is not None:
            try:
                sock.close()
            except Exception:
                pass

    def status(self) -> dict[str, Any]:
        return {
            "transport": "STRATUM_V1_TLS",
            "connected": self.connected,
            "tls_required": True,
            "certificate_validation": "SSL_CONTEXT_DEFAULT_VERIFICATION",
            "network_access_performed_by_status": False,
            "credentials_logged": False,
            "live_mining_verified": False,
            "revenue_verified": False,
        }

    def __enter__(self) -> "StratumV1TLSTransport":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()
