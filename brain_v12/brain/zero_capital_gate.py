"""Zero-capital revenue gate for Electronic Brain.

A hard policy layer for revenue opportunities that must operate with no user
capital. It rejects deposits, prepaid contracts, paid cloud resources, required
subscriptions, and any direct cost above zero. Expected revenue is never treated
as realized revenue.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any
import re


@dataclass(frozen=True)
class GateResult:
    eligible: bool
    status: str
    reason: str
    direct_cost_jod: float
    expected_revenue_jod: float
    expected_net_jod: float
    capital_required_jod: float
    flags: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self) | {"flags": list(self.flags)}


class ZeroCapitalGate:
    """Allow only opportunities that require zero upfront capital."""

    BLOCK_PATTERNS = (
        r"deposit", r"upfront", r"prepaid", r"pre[- ]?pay", r"buy (?:a )?(?:plan|contract|license)",
        r"subscription required", r"paid plan", r"paid cloud", r"purchase", r"investment required",
        r"إيداع", r"دفعة مقدمة", r"مقدم", r"اشتراك مدفوع", r"خطة مدفوعة",
        r"شراء", r"استثمار مطلوب", r"رأس مال", r"عقد تعدين مدفوع", r"تعدين سحابي مدفوع",
    )

    @classmethod
    def evaluate(cls, item: dict[str, Any], available_capital_jod: float = 0.0) -> GateResult:
        capital = max(float(available_capital_jod or 0), 0.0)
        direct = max(float(item.get("direct_cost_jod", item.get("cost", 0)) or 0), 0.0)
        expected = max(float(item.get("expected_revenue_jod", item.get("expected_jod", 0)) or 0), 0.0)
        declared_required = max(float(item.get("capital_required_jod", 0) or 0), 0.0)
        text = " ".join(str(item.get(k, "")) for k in (
            "title", "description", "requirements", "evidence", "action", "terms"
        )).lower()
        flags = tuple(p for p in cls.BLOCK_PATTERNS if re.search(p, text, re.I))
        required = max(direct, declared_required)
        if flags:
            return GateResult(False, "REJECTED", "CAPITAL_OR_PAYMENT_REQUIRED", direct, expected,
                              round(expected - direct, 2), required, flags)
        if required > capital or required > 0:
            return GateResult(False, "REJECTED", "NONZERO_CAPITAL_REQUIRED", direct, expected,
                              round(expected - direct, 2), required, ())
        return GateResult(True, "ELIGIBLE", "ZERO_CAPITAL", direct, expected,
                          round(expected - direct, 2), 0.0, ())

    @classmethod
    def filter(cls, items: list[dict[str, Any]], available_capital_jod: float = 0.0) -> list[dict[str, Any]]:
        accepted = []
        for item in items or []:
            result = cls.evaluate(item, available_capital_jod)
            row = dict(item)
            row["zero_capital_gate"] = result.to_dict()
            if result.eligible:
                accepted.append(row)
        return accepted
