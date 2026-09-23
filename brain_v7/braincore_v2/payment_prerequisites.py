"""Runtime contract for real-payment prerequisites.

No secret, PIN, OTP, card data, or wallet credential is accepted here.
The adapter only consumes non-sensitive capability signals from the configured
provider and fails closed when any prerequisite is missing.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class PaymentPrerequisites:
    provider_connected: bool
    balance_usd: float | None
    recipient_verified: bool
    authorization_verified: bool
    provider_reference: str | None = None
    provider_status: str | None = None

    def validate_for_1000_usd(self) -> tuple[bool, tuple[str, ...]]:
        blockers: list[str] = []
        if not self.provider_connected:
            blockers.append("PAYMENT_PROVIDER_NOT_CONNECTED")
        if self.balance_usd is None:
            blockers.append("BALANCE_UNKNOWN")
        elif self.balance_usd < 1000:
            blockers.append("INSUFFICIENT_USD_BALANCE")
        if not self.recipient_verified:
            blockers.append("RECIPIENT_NOT_VERIFIED")
        if not self.authorization_verified:
            blockers.append("EXPLICIT_AUTHORIZATION_REQUIRED")
        return (not blockers, tuple(blockers))

    def reconcile_provider_result(self, amount_usd: float) -> tuple[bool, str]:
        if not self.provider_reference:
            return False, "PROVIDER_REFERENCE_MISSING"
        if amount_usd != 1000:
            return False, "AMOUNT_MISMATCH"
        status = (self.provider_status or "").upper()
        if status in {"CONFIRMED", "COMPLETED", "SETTLED"}:
            return True, "PROVIDER_CONFIRMED"
        if status in {"PENDING", "PROCESSING"}:
            return False, "PROVIDER_PENDING"
        return False, "PROVIDER_NOT_CONFIRMED"
