"""Controlled verification state machine for crypto mining opportunities.

No provider credentials, withdrawals, purchases, or blockchain calls are made here.
Collectors submit evidence; this module decides whether the evidence is sufficient.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from .crypto_mining_intelligence import PayoutEvidence, verify_payout


class VerificationState(StrEnum):
    DISCOVERED = "DISCOVERED"
    RISK_CHECK = "RISK_CHECK"
    FREE_TEST = "FREE_TEST"
    MEASURE = "MEASURE"
    WITHDRAWAL_TEST = "WITHDRAWAL_TEST"
    BLOCKCHAIN_VERIFY = "BLOCKCHAIN_VERIFY"
    REVENUE_REALIZED = "REVENUE_REALIZED"
    REJECTED = "REJECTED"


@dataclass
class MiningVerificationCycle:
    opportunity_id: str
    provider: str
    state: VerificationState = VerificationState.DISCOVERED
    evidence: dict[str, Any] = field(default_factory=dict)
    history: list[str] = field(default_factory=lambda: [VerificationState.DISCOVERED.value])

    def advance(self, new_state: VerificationState, reason: str) -> dict[str, Any]:
        allowed = {
            VerificationState.DISCOVERED: {VerificationState.RISK_CHECK, VerificationState.REJECTED},
            VerificationState.RISK_CHECK: {VerificationState.FREE_TEST, VerificationState.REJECTED},
            VerificationState.FREE_TEST: {VerificationState.MEASURE, VerificationState.REJECTED},
            VerificationState.MEASURE: {VerificationState.WITHDRAWAL_TEST, VerificationState.REJECTED},
            VerificationState.WITHDRAWAL_TEST: {VerificationState.BLOCKCHAIN_VERIFY, VerificationState.REJECTED},
            VerificationState.BLOCKCHAIN_VERIFY: {VerificationState.REVENUE_REALIZED, VerificationState.REJECTED},
            VerificationState.REVENUE_REALIZED: set(),
            VerificationState.REJECTED: set(),
        }
        if new_state not in allowed[self.state]:
            raise ValueError(f"invalid transition {self.state}->{new_state}")
        self.state = new_state
        self.history.append(new_state.value)
        self.evidence["last_reason"] = reason
        return self.snapshot()

    def submit_payout_evidence(self, payout: PayoutEvidence) -> dict[str, Any]:
        result = verify_payout(payout)
        self.evidence["payout_verification"] = result
        if self.state == VerificationState.WITHDRAWAL_TEST and result["status"] == "VERIFIED_COMPLETED":
            self.advance(VerificationState.BLOCKCHAIN_VERIFY, "payout contains transaction evidence")
            self.advance(VerificationState.REVENUE_REALIZED, "all payout evidence gates passed")
        elif result["status"].startswith("REJECTED"):
            if self.state not in {VerificationState.REVENUE_REALIZED, VerificationState.REJECTED}:
                self.advance(VerificationState.REJECTED, result["status"])
        return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "provider": self.provider,
            "state": self.state.value,
            "history": list(self.history),
            "evidence": dict(self.evidence),
            "guardrails": {
                "free_only": True,
                "payments_enabled": False,
                "provider_credentials_required": False,
                "brain_moves_funds": False,
                "realized_requires_payout_and_chain_evidence": True,
            },
        }


def start_cloud_mining_verification(provider: str, opportunity_id: str) -> MiningVerificationCycle:
    if not provider.strip() or not opportunity_id.strip():
        raise ValueError("provider and opportunity_id are required")
    return MiningVerificationCycle(opportunity_id=opportunity_id, provider=provider)
