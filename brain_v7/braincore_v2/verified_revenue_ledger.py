"""Revenue evidence and anti-double-counting ledger.

Revenue is recognized only once, after provider/order/payment evidence is
attached. The ledger stores hashes of evidence references rather than secrets.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
from typing import Any


@dataclass(frozen=True)
class RevenueReceipt:
    receipt_id: str
    source: str
    external_id: str
    amount_jod: float
    evidence_hash: str
    recorded_at: float
    verified: bool = True


class VerifiedRevenueLedger:
    def __init__(self) -> None:
        self._receipts: dict[str, RevenueReceipt] = {}

    @staticmethod
    def _key(source: str, external_id: str) -> str:
        return sha256(f"{source}:{external_id}".encode("utf-8")).hexdigest()

    @staticmethod
    def evidence_hash(evidence: str) -> str:
        return sha256(evidence.encode("utf-8")).hexdigest()

    def record(
        self,
        *,
        source: str,
        external_id: str,
        amount_jod: float,
        evidence: str,
        recorded_at: float,
    ) -> dict[str, Any]:
        if not source.strip() or not external_id.strip():
            raise ValueError("source and external_id are required")
        amount = float(amount_jod)
        if amount < 0:
            raise ValueError("amount_jod must be non-negative")
        key = self._key(source, external_id)
        if key in self._receipts:
            return {"status": "DUPLICATE_IGNORED", "receipt": asdict(self._receipts[key])}
        receipt = RevenueReceipt(
            receipt_id=key[:16],
            source=source.strip(),
            external_id=external_id.strip(),
            amount_jod=round(amount, 2),
            evidence_hash=self.evidence_hash(evidence),
            recorded_at=float(recorded_at),
        )
        self._receipts[key] = receipt
        return {"status": "RECORDED", "receipt": asdict(receipt)}

    def total_jod(self) -> float:
        return round(sum(r.amount_jod for r in self._receipts.values() if r.verified), 2)

    def snapshot(self) -> dict[str, Any]:
        return {
            "receipts": len(self._receipts),
            "verified_revenue_jod": self.total_jod(),
            "items": [asdict(x) for x in self._receipts.values()],
            "secrets_stored": False,
        }
