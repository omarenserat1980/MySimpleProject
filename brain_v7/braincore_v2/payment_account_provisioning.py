"""Provisioning plan for a real payment account.

The brain can prepare and validate everything around account onboarding, but
cannot impersonate the owner, pass KYC, accept provider terms, or fabricate
credentials. This module turns the missing external dependency into an explicit
deployment checklist and secure injection contract.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class PaymentAccountRequirement:
    provider: str
    country: str
    currency: str
    kyc_required: bool = True
    credentials_required: bool = True

@dataclass(frozen=True)
class ProvisioningStatus:
    status: str
    blockers: tuple[str, ...]
    next_actions: tuple[str, ...]

def build_provisioning_status(*, provider_connected: bool,
                              identity_verified: bool,
                              credentials_in_secret_store: bool,
                              webhook_verified: bool) -> ProvisioningStatus:
    blockers=[]
    if not provider_connected: blockers.append("PAYMENT_PROVIDER_NOT_CONNECTED")
    if not identity_verified: blockers.append("OWNER_KYC_NOT_VERIFIED")
    if not credentials_in_secret_store: blockers.append("PROVIDER_CREDENTIALS_NOT_IN_SECRET_STORE")
    if not webhook_verified: blockers.append("PROVIDER_WEBHOOK_NOT_VERIFIED")
    if blockers:
        return ProvisioningStatus(
            "BLOCKED_EXTERNAL_PROVISIONING", tuple(blockers),
            ("Create/verify the payment account with the provider.",
             "Complete owner identity/KYC with the provider.",
             "Inject credentials through the deployment secret manager, never source/chat.",
             "Configure and verify provider callbacks before enabling transfers.")
        )
    return ProvisioningStatus(
        "READY_FOR_REAL_PROVIDER_TEST",
        (),
        ("Run a provider-supported test/readiness check.",
         "Require explicit authorization for each transfer.",
         "Require provider confirmation before recording success.")
    )
