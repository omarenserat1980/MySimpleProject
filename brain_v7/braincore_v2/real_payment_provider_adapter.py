"""Production payment-provider boundary.

This adapter intentionally contains no provider-specific endpoint or secret.
A deployment supplies a provider implementation through dependency injection.
The core can therefore execute a real transfer only when an authenticated
provider has been configured externally.

Never put API keys, PINs, card numbers, wallet credentials, or session tokens
in this module, GitHub, or the brain state.
"""
from __future__ import annotations
from typing import Any, Protocol
from .payment_provider import TransferResult


class RealProviderClient(Protocol):
    def submit_transfer(self, *, amount_jod: float, destination_ref: str,
                        idempotency_key: str) -> dict[str, Any]:
        ...

    def get_transfer_status(self, *, provider_reference: str) -> dict[str, Any]:
        ...


class RealPaymentProviderAdapter:
    """Translate an authenticated provider client into the brain contract."""

    def __init__(self, client: RealProviderClient) -> None:
        if client is None:
            raise ValueError("AUTHENTICATED_PROVIDER_CLIENT_REQUIRED")
        self.client = client

    def submit(self, amount_jod: float, destination_ref: str,
               idempotency_key: str) -> TransferResult:
        result = self.client.submit_transfer(
            amount_jod=round(float(amount_jod), 2),
            destination_ref=str(destination_ref),
            idempotency_key=str(idempotency_key),
        )
        reference = str(result.get("provider_reference", "")).strip()
        status = str(result.get("status", "")).upper()
        if not reference:
            return TransferResult(
                status="FAILED",
                error_code="PROVIDER_REFERENCE_MISSING",
            )
        return TransferResult(
            status=status or "SUBMITTED",
            provider_reference=reference,
            amount_jod=float(result["amount_jod"])
            if result.get("amount_jod") is not None else round(float(amount_jod), 2),
            error_code=result.get("error_code"),
        )

    def status(self, provider_reference: str) -> TransferResult:
        reference = str(provider_reference).strip()
        if not reference:
            raise ValueError("PROVIDER_REFERENCE_REQUIRED")
        result = self.client.get_transfer_status(
            provider_reference=reference
        )
        return TransferResult(
            status=str(result.get("status", "")).upper() or "PENDING",
            provider_reference=reference,
            amount_jod=(
                float(result["amount_jod"])
                if result.get("amount_jod") is not None else None
            ),
            error_code=result.get("error_code"),
        )
