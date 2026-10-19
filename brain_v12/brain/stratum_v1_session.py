"""Explicitly driven Stratum V1 session coordinator.

This composes the protocol contract and TLS transport but never connects or starts
work automatically. It does not construct mining jobs or submit shares. Callers
must explicitly connect and invoke subscribe/authorize; share submission remains
intentionally unimplemented until the full mining execution gate is reviewed.
"""
from __future__ import annotations

from typing import Any

from .stratum_v1_adapter_contract import StratumV1AdapterContract
from .stratum_v1_tls_transport import StratumV1TLSTransport, StratumTransportError


class StratumV1Session:
    def __init__(
        self,
        worker_name: str,
        transport: StratumV1TLSTransport,
    ) -> None:
        if not isinstance(transport, StratumV1TLSTransport):
            raise ValueError("TLS_STRATUM_TRANSPORT_REQUIRED")
        self.adapter = StratumV1AdapterContract(worker_name)
        self.transport = transport

    def connect(self, *, explicit_approval: bool, approved_host: str) -> None:
        """Connect only when the caller confirms the exact configured host."""
        self.transport.connect(
            explicit_approval=explicit_approval,
            approved_host=approved_host,
        )

    def subscribe(self) -> dict[str, Any]:
        self._require_connected()
        message = self.adapter.request("mining.subscribe", [])
        self.transport.send_message(message)
        return {"status": "SUBSCRIBE_SENT", "request_id": message["id"]}

    def authorize(self, password: str) -> dict[str, Any]:
        self._require_connected()
        if not isinstance(password, str) or not password:
            raise ValueError("WORKER_PASSWORD_REQUIRED")
        message = self.adapter.request(
            "mining.authorize", [self.adapter.worker_name, password]
        )
        self.transport.send_message(message)
        # Do not retain or return the password in session state/results.
        return {"status": "AUTHORIZE_SENT", "request_id": message["id"]}

    def process_one(self) -> dict[str, Any]:
        """Process one received protocol message; never submits a share."""
        self._require_connected()
        message = self.transport.receive_message()
        if message.get("id") is None:
            result = self.adapter.handle_notification(message)
            return {
                "message_type": "notification",
                "result": result,
                "share_submission_enabled": False,
            }
        result = self.adapter.handle_response(message)
        return {
            "message_type": "response",
            "result": result,
            "share_submission_enabled": False,
        }

    def submit_share(self, *_args: Any, **_kwargs: Any) -> None:
        """Fail closed: candidate validation is not live share-submission authority."""
        raise StratumTransportError("LIVE_SHARE_SUBMISSION_NOT_IMPLEMENTED")

    def close(self) -> None:
        self.transport.close()

    def status(self) -> dict[str, Any]:
        return {
            "session_mode": "EXPLICIT_STRATUM_SESSION_NO_SHARE_SUBMISSION",
            "connected": self.transport.connected,
            "protocol": self.adapter.status(),
            "share_submission_enabled": False,
            "live_mining_verified": False,
            "payout_verified": False,
            "revenue_verified": False,
        }

    def _require_connected(self) -> None:
        if not self.transport.connected:
            raise StratumTransportError("TRANSPORT_NOT_CONNECTED")

    def __enter__(self) -> "StratumV1Session":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()
