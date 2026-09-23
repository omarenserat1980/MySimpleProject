"""Live payment gate for the electronic brain.

This module validates configuration only. It never creates accounts, bypasses KYC,
or moves money. Real credentials must be supplied through an external secret
manager/environment and are never returned by this module.
"""
from dataclasses import dataclass
import os


@dataclass(frozen=True)
class LivePaymentGate:
    provider_name: str
    live_mode: bool
    provider_connected: bool
    credentials_present: bool
    webhook_verified: bool
    mock_provider: bool
    blockers: tuple[str, ...]

    @property
    def ready(self) -> bool:
        return self.live_mode and not self.blockers


def _present(name: str, env: dict[str, str]) -> bool:
    value = env.get(name, "")
    return bool(value and value.strip())


def inspect_live_payment_gate(env: dict[str, str] | None = None) -> LivePaymentGate:
    """Inspect safe runtime signals without exposing credential values.

    Expected runtime variables:
      PAYMENT_LIVE_MODE=true
      PAYMENT_PROVIDER_NAME=<provider>
      PAYMENT_PROVIDER_CONNECTED=true
      PAYMENT_CREDENTIALS_PRESENT=true
      PAYMENT_WEBHOOK_VERIFIED=true
      PAYMENT_PROVIDER_KIND=real
    """
    e = dict(os.environ if env is None else env)
    blockers: list[str] = []
    live_mode = e.get("PAYMENT_LIVE_MODE", "").lower() == "true"
    provider = e.get("PAYMENT_PROVIDER_NAME", "").strip() or "UNSET"
    connected = e.get("PAYMENT_PROVIDER_CONNECTED", "").lower() == "true"
    credentials = e.get("PAYMENT_CREDENTIALS_PRESENT", "").lower() == "true"
    webhook = e.get("PAYMENT_WEBHOOK_VERIFIED", "").lower() == "true"
    provider_kind = e.get("PAYMENT_PROVIDER_KIND", "").strip().lower()

    if not live_mode:
        blockers.append("LIVE_MODE_DISABLED")
    if provider == "UNSET":
        blockers.append("PAYMENT_PROVIDER_NOT_CONFIGURED")
    if not connected:
        blockers.append("PAYMENT_PROVIDER_NOT_CONNECTED")
    if not credentials:
        blockers.append("PROVIDER_CREDENTIALS_NOT_IN_SECRET_STORE")
    if not webhook:
        blockers.append("PROVIDER_WEBHOOK_NOT_VERIFIED")
    if provider_kind != "real":
        blockers.append("REAL_PROVIDER_REQUIRED")
    if e.get("PAYMENT_PROVIDER_KIND", "").strip().lower() == "mock":
        blockers.append("MOCK_PROVIDER_BLOCKED_IN_LIVE_MODE")

    return LivePaymentGate(
        provider_name=provider,
        live_mode=live_mode,
        provider_connected=connected,
        credentials_present=credentials,
        webhook_verified=webhook,
        mock_provider=provider_kind == "mock",
        blockers=tuple(dict.fromkeys(blockers)),
    )
