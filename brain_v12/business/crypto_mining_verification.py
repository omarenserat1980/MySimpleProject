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


@dataclass(frozen=True)
class BlockchainProof:
    txid: str
    explorer_url: str
    confirmations: int
    chain_status: str = "CONFIRMED"
    verified_at: str = ""

    def validate(self) -> None:
        if not self.txid.strip() or not self.explorer_url.strip():
            raise ValueError("txid and explorer_url are required")
        if self.confirmations < 1:
            raise ValueError("at least one confirmation is required")
        if self.chain_status.upper() != "CONFIRMED":
            raise ValueError("chain_status must be CONFIRMED")
        if not self.verified_at.strip():
            raise ValueError("verified_at is required")


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
        self.evidence["payout_txid"] = payout.txid
        if self.state == VerificationState.WITHDRAWAL_TEST and result["status"] == "VERIFIED_COMPLETED":
            self.advance(
                VerificationState.BLOCKCHAIN_VERIFY,
                "payout evidence passed; explicit chain proof required",
            )
        elif result["status"].startswith("REJECTED"):
            if self.state not in {VerificationState.REVENUE_REALIZED, VerificationState.REJECTED}:
                self.advance(VerificationState.REJECTED, result["status"])
        return self.snapshot()

    def submit_blockchain_proof(self, proof: BlockchainProof) -> dict[str, Any]:
        if self.state != VerificationState.BLOCKCHAIN_VERIFY:
            raise ValueError("blockchain proof is only accepted in BLOCKCHAIN_VERIFY")
        proof.validate()
        payout = self.evidence.get("payout_verification", {})
        checks = payout.get("checks", {})
        expected_txid = self.evidence.get("payout_txid")
        if payout.get("status") != "VERIFIED_COMPLETED" or not checks.get("on_chain_proof") or not expected_txid:
            raise ValueError("verified payout evidence is required before blockchain proof")
        if proof.txid != expected_txid:
            raise ValueError("blockchain proof txid does not match payout evidence")
        self.evidence["blockchain_proof"] = {
            "txid": proof.txid,
            "explorer_url": proof.explorer_url,
            "confirmations": proof.confirmations,
            "chain_status": proof.chain_status,
            "verified_at": proof.verified_at,
        }
        self.advance(
            VerificationState.REVENUE_REALIZED,
            "explicit confirmed blockchain proof matched payout",
        )
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
