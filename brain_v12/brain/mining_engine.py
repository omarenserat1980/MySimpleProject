"""Mining economics engine for Electronic Brain V12.

This module is deliberately an analysis layer: it does not mine, buy hardware,
connect wallets, or count projected revenue as verified income. It evaluates a
user-supplied mining configuration using explicit inputs and conservative
accounting.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class MiningInput:
    algorithm: str
    hashrate: float
    hashrate_unit: str
    power_watts: float
    electricity_jod_per_kwh: float
    gross_revenue_jod_per_day: float
    hardware_cost_jod: float = 0.0
    pool_fee_percent: float = 0.0
    other_daily_cost_jod: float = 0.0


class MiningEngine:
    """Calculate mining economics without asserting live profitability."""

    UNITS_TO_HS = {
        "H": 1.0,
        "KH": 1_000.0,
        "MH": 1_000_000.0,
        "GH": 1_000_000_000.0,
        "TH": 1_000_000_000_000.0,
        "PH": 1_000_000_000_000_000.0,
    }

    def normalize_hashrate(self, value: float, unit: str) -> float:
        unit = str(unit).upper().strip()
        if unit not in self.UNITS_TO_HS:
            raise ValueError("INVALID_HASHRATE_UNIT")
        value = float(value)
        if value < 0:
            raise ValueError("INVALID_HASHRATE")
        return value * self.UNITS_TO_HS[unit]

    def analyze(self, data: MiningInput | dict[str, Any]) -> dict[str, Any]:
        item = data if isinstance(data, MiningInput) else MiningInput(**data)
        if item.power_watts < 0 or item.electricity_jod_per_kwh < 0:
            raise ValueError("INVALID_POWER_OR_ELECTRICITY")
        if item.gross_revenue_jod_per_day < 0 or item.hardware_cost_jod < 0:
            raise ValueError("INVALID_REVENUE_OR_HARDWARE_COST")
        if not 0 <= item.pool_fee_percent < 100:
            raise ValueError("INVALID_POOL_FEE")
        if item.other_daily_cost_jod < 0:
            raise ValueError("INVALID_OTHER_COST")

        hashrate_hs = self.normalize_hashrate(item.hashrate, item.hashrate_unit)
        kwh_day = item.power_watts * 24.0 / 1000.0
        electricity_day = kwh_day * item.electricity_jod_per_kwh
        pool_fee = item.gross_revenue_jod_per_day * item.pool_fee_percent / 100.0
        net_day = item.gross_revenue_jod_per_day - electricity_day - pool_fee - item.other_daily_cost_jod
        net_month = net_day * 30.0
        break_even_days = (
            item.hardware_cost_jod / net_day if item.hardware_cost_jod > 0 and net_day > 0 else None
        )

        return {
            "ok": True,
            "status": "PROFITABLE_ON_INPUTS" if net_day > 0 else "NOT_PROFITABLE_ON_INPUTS",
            "algorithm": item.algorithm,
            "hashrate_hs": hashrate_hs,
            "power_watts": item.power_watts,
            "energy_kwh_per_day": round(kwh_day, 6),
            "gross_revenue_jod_per_day": round(item.gross_revenue_jod_per_day, 6),
            "electricity_jod_per_day": round(electricity_day, 6),
            "pool_fee_jod_per_day": round(pool_fee, 6),
            "other_cost_jod_per_day": round(item.other_daily_cost_jod, 6),
            "net_jod_per_day": round(net_day, 6),
            "net_jod_per_30_days": round(net_month, 6),
            "hardware_cost_jod": round(item.hardware_cost_jod, 6),
            "break_even_days": round(break_even_days, 2) if break_even_days is not None else None,
            "revenue_verification": "UNVERIFIED",
            "live_market_data": False,
            "note": "النتيجة حسابية من المدخلات فقط؛ لا تثبت ربحًا فعليًا أو دخلًا محققًا.",
        }

    def compare(self, candidates: list[MiningInput | dict[str, Any]]) -> dict[str, Any]:
        results = [self.analyze(item) for item in candidates]
        ranked = sorted(results, key=lambda x: x["net_jod_per_day"], reverse=True)
        return {
            "ok": True,
            "count": len(results),
            "candidates": results,
            "order": [x["algorithm"] for x in ranked],
            "ranking_basis": "net_jod_per_day_from_supplied_inputs",
            "warning": "هذا ترتيب حسابي للمدخلات المقدمة وليس not a recommendation؛ وليس توصية استثمارية أو توقعًا للسوق.",
        }

    def snapshot(self) -> dict[str, Any]:
        return {
            "ok": True,
            "module": "mining_economics",
            "live_data_connected": False,
            "execution": "ANALYSIS_ONLY",
            "verified_revenue_jod": 0.0,
            "supported_hashrate_units": sorted(self.UNITS_TO_HS),
        }
