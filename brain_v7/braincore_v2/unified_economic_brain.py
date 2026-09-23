"""Unified economic brain: evidence-first decision layer.

Combines opportunity economics with payment-provider readiness. It does not
move funds, submit jobs, or claim profit; execution remains separately gated.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

from .economic_controller import evaluate
from .payment_provider_selector import ProviderSnapshot, choose_provider


@dataclass(frozen=True)
class EconomicState:
    cash_jod: float | None
    verified_profit_jod: float
    candidate_expected_jod: float
    risk_clear: bool
    provider_status: str
    selected_provider: str | None


@dataclass(frozen=True)
class UnifiedDecision:
    status: str
    action: str
    reason: str
    state: EconomicState


def assess_financial_state(
    *,
    cash_jod: float | None,
    verified_profit_jod: float,
    candidate_expected_jod: float,
    risk_clear: bool,
    transfer_amount_jod: float,
    providers: list[ProviderSnapshot],
    destination_ref: str,
) -> UnifiedDecision:
    provider = choose_provider(transfer_amount_jod, providers, destination_ref)
    state = EconomicState(
        cash_jod=cash_jod,
        verified_profit_jod=verified_profit_jod,
        candidate_expected_jod=candidate_expected_jod,
        risk_clear=risk_clear,
        provider_status=provider.status,
        selected_provider=provider.provider,
    )
    if not risk_clear:
        return UnifiedDecision("REVIEW_REQUIRED", "HOLD",
                               "Risk/compliance state is not clear.", state)
    if cash_jod is None:
        return UnifiedDecision("NOT_READY", "RESEARCH",
                               "Actual available cash is unknown.", state)
    if cash_jod < transfer_amount_jod:
        return UnifiedDecision("INSUFFICIENT_FUNDS", "HOLD",
                               "Known cash balance is below requested amount.", state)
    if provider.status != "READY_FOR_PROVIDER_SELECTION":
        return UnifiedDecision("NO_PAYMENT_ROUTE", "HOLD",
                               "No configured provider passed readiness checks.", state)
    return UnifiedDecision(
        "READY_FOR_AUTHORIZED_EXECUTION", "PREPARE_TRANSFER",
        "Financial state and an external provider route are ready; explicit authorization remains required.",
        state,
    )
