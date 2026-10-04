"""Payment idempotency guard.

Prevents the same logical payment operation from being accepted twice.
This is a safety primitive; it does not verify money.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PaymentIntent:
    order_id: str
    idempotency_key: str
    provider_id: str
    amount_minor: int
    currency: str


class PaymentIdempotencyGuard:
    def __init__(self) -> None:
        self._seen: dict[str, PaymentIntent] = {}

    def register(self, intent: PaymentIntent) -> bool:
        existing = self._seen.get(intent.idempotency_key)
        if existing is None:
            self._seen[intent.idempotency_key] = intent
            return True
        if existing == intent:
            return False
        raise ValueError("IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_INTENT")

    def lookup(self, idempotency_key: str) -> PaymentIntent | None:
        return self._seen.get(idempotency_key)

    def clear_for_testing(self) -> None:
        self._seen.clear()
