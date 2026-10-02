"""Evidence-first crypto mining economics and payout verification.

The verifier never logs into a provider, moves funds, or treats an in-app
balance as realized revenue. It only evaluates evidence supplied by an
authorized collector/user.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
import hashlib
import json


@dataclass(frozen=True)
class MiningMachine:
    machine_id: str
    hashrate_th: float
    efficiency_j_th: float
    hardware_cost_usd: float = 0.0
    uptime_pct: float = 100.0
    pool_fee_pct: float = 0.0
    other_daily_cost_usd: float = 0.0

    def validate(self) -> None:
        if not self.machine_id.strip():
            raise ValueError("machine_id is required")
        if self.hashrate_th <= 0 or self.efficiency_j_th <= 0:
            raise ValueError("hashrate and efficiency must be > 0")
        if self.hardware_cost_usd < 0 or self.other_daily_cost_usd < 0:
            raise ValueError("costs must be >= 0")
        if not 0 < self.uptime_pct <= 100:
            raise ValueError("uptime_pct must be in (0, 100]")
        if not 0 <= self.pool_fee_pct < 100:
            raise ValueError("pool_fee_pct must be in [0, 100)")


@dataclass(frozen=True)
class NetworkSnapshot:
    asset: str
    hashprice_usd_per_th_day: float
    observed_at: str
    source: str
    btc_price_usd: float | None = None
    network_hashrate_eh: float | None = None
    difficulty: float | None = None
    block_subsidy_btc: float | None = None
    evidence_urls: tuple[str, ...] = ()

    def validate(self) -> None:
        if not self.asset.strip():
            raise ValueError("asset is required")
        if self.hashprice_usd_per_th_day <= 0:
            raise ValueError("hashprice must be > 0")
        if not self.observed_at.strip() or not self.source.strip():
            raise ValueError("observed_at and source are required")


@dataclass
class MiningAnalysis:
    machine_id: str
    asset: str
    status: str
    gross_daily_revenue_usd: float
    pool_fee_daily_usd: float
    electricity_kwh_daily: float
    electricity_cost_daily_usd: float
    other_daily_cost_usd: float
    net_daily_profit_usd: float
    break_even_electricity_usd_kwh: float
    monthly_net_profit_usd: float
    hardware_payback_days: float | None
    annualized_simple_return_pct: float | None
    evidence: list[str] = field(default_factory=list)
    assumptions: dict[str, Any] = field(default_factory=dict)

    def snapshot(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PayoutEvidence:
    provider: str
    observed_at: str
    balance_btc: float
    withdrawal_requested_btc: float
    network: str
    destination_fingerprint: str
    txid: str = ""
    explorer_url: str = ""
    received_btc: float = 0.0
    fee_btc: float = 0.0
    source_url: str = ""
    evidence_sha256: str = ""

    def validate(self) -> None:
        if not self.provider.strip() or not self.observed_at.strip():
            raise ValueError("provider and observed_at are required")
        if self.balance_btc < 0 or self.withdrawal_requested_btc < 0:
            raise ValueError("BTC amounts must be >= 0")
        if self.received_btc < 0 or self.fee_btc < 0:
            raise ValueError("received_btc and fee_btc must be >= 0")
        if not self.destination_fingerprint.strip():
            raise ValueError("destination_fingerprint is required")


def _evidence_digest(evidence: PayoutEvidence) -> str:
    payload = asdict(evidence)
    payload["evidence_sha256"] = ""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_payout(evidence: PayoutEvidence) -> dict[str, Any]:
    """Classify payout evidence without contacting the provider or blockchain."""
    evidence.validate()
    checks = {
        "provider_identified": bool(evidence.provider.strip()),
        "withdrawal_requested": evidence.withdrawal_requested_btc > 0,
        "destination_identified": bool(evidence.destination_fingerprint.strip()),
        "txid_present": bool(evidence.txid.strip()),
        "received_amount_present": evidence.received_btc > 0,
        "received_not_greater_than_requested": (
            evidence.received_btc <= evidence.withdrawal_requested_btc
        ),
    }
    expected_digest = _evidence_digest(evidence)
    checks["evidence_integrity"] = (
        not evidence.evidence_sha256 or evidence.evidence_sha256 == expected_digest
    )
    on_chain_proof = bool(evidence.txid.strip() and evidence.explorer_url.strip())
    checks["on_chain_proof"] = on_chain_proof

    if all(checks.values()) and on_chain_proof:
        status = "VERIFIED_COMPLETED"
        financial_state = "REVENUE_REALIZED"
    elif checks["withdrawal_requested"] and not checks["received_amount_present"]:
        status = "PENDING_WITHDRAWAL_EVIDENCE"
        financial_state = "EXPECTED"
    elif not checks["evidence_integrity"]:
        status = "REJECTED_EVIDENCE_INTEGRITY"
        financial_state = "UNVERIFIED"
    else:
        status = "REJECTED_INCOMPLETE_EVIDENCE"
        financial_state = "UNVERIFIED"

    return {
        "status": status,
        "financial_state": financial_state,
        "checks": checks,
        "evidence_sha256": expected_digest,
        "net_received_btc": round(evidence.received_btc, 14),
        "fee_btc": round(evidence.fee_btc, 14),
        "guardrails": {
            "provider_login": False,
            "funds_moved_by_brain": False,
            "auto_purchase": False,
            "auto_withdrawal": False,
            "seed_phrase_requested": False,
        },
    }


def analyze_mining(machine: MiningMachine, network: NetworkSnapshot,
                   electricity_usd_kwh: float,
                   market_freshness: str = "UNKNOWN") -> MiningAnalysis:
    machine.validate()
    network.validate()
    if electricity_usd_kwh < 0:
        raise ValueError("electricity_usd_kwh must be >= 0")

    uptime = machine.uptime_pct / 100.0
    gross = machine.hashrate_th * network.hashprice_usd_per_th_day * uptime
    pool_fee = gross * (machine.pool_fee_pct / 100.0)
    net_after_pool = gross - pool_fee
    power_kw = machine.hashrate_th * machine.efficiency_j_th / 1000.0
    kwh_day = power_kw * 24.0 * uptime
    electricity_cost = kwh_day * electricity_usd_kwh
    profit = net_after_pool - electricity_cost - machine.other_daily_cost_usd
    breakeven = ((net_after_pool - machine.other_daily_cost_usd) / kwh_day
                 if kwh_day > 0 else 0.0)
    monthly = profit * 30.0
    payback = (machine.hardware_cost_usd / profit
               if machine.hardware_cost_usd > 0 and profit > 0 else None)
    annual_return = ((profit * 365.0 / machine.hardware_cost_usd) * 100.0
                     if machine.hardware_cost_usd > 0 and profit > 0 else None)
    status = "HUMAN_APPROVAL" if profit > 0 else "WAIT" if profit < 0 else "RESEARCH"

    return MiningAnalysis(
        machine_id=machine.machine_id, asset=network.asset, status=status,
        gross_daily_revenue_usd=round(gross, 6),
        pool_fee_daily_usd=round(pool_fee, 6),
        electricity_kwh_daily=round(kwh_day, 6),
        electricity_cost_daily_usd=round(electricity_cost, 6),
        other_daily_cost_usd=round(machine.other_daily_cost_usd, 6),
        net_daily_profit_usd=round(profit, 6),
        break_even_electricity_usd_kwh=round(max(breakeven, 0.0), 6),
        monthly_net_profit_usd=round(monthly, 6),
        hardware_payback_days=round(payback, 2) if payback is not None else None,
        annualized_simple_return_pct=round(annual_return, 2) if annual_return is not None else None,
        evidence=list(network.evidence_urls),
        assumptions={
            "hashprice_usd_per_th_day": network.hashprice_usd_per_th_day,
            "electricity_usd_kwh": electricity_usd_kwh,
            "uptime_pct": machine.uptime_pct,
            "pool_fee_pct": machine.pool_fee_pct,
            "hardware_cost_usd": machine.hardware_cost_usd,
            "other_daily_cost_usd": machine.other_daily_cost_usd,
            "network_observed_at": network.observed_at,
            "network_source": network.source,
            "result_class": "EXPECTED_ONLY",
            "market_freshness": market_freshness,
        },
    )


def compare_electricity_prices(machine: MiningMachine, network: NetworkSnapshot,
                               prices_usd_kwh: list[float]) -> list[dict[str, Any]]:
    return [analyze_mining(machine, network, price).snapshot() for price in prices_usd_kwh]


def build_intelligence_report(machine: MiningMachine, network: NetworkSnapshot,
                               electricity_usd_kwh: float,
                               sensitivity_prices: list[float] | None = None) -> dict[str, Any]:
    analysis = analyze_mining(machine, network, electricity_usd_kwh)
    report: dict[str, Any] = {
        "engine": "Crypto Mining Intelligence",
        "version": "1.1",
        "decision_state": analysis.status,
        "analysis": analysis.snapshot(),
        "guardrails": {
            "trading_enabled": False,
            "purchase_enabled": False,
            "external_contact_enabled": False,
            "financial_state": "EXPECTED",
            "requires_human_approval_for_external_action": True,
        },
    }
    if sensitivity_prices:
        report["electricity_sensitivity"] = compare_electricity_prices(
            machine, network, sensitivity_prices
        )
    return report
