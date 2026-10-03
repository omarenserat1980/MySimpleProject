"""Tests for Brain monetization registry."""
import unittest

from brain_v12.business.monetization_registry import (
    MonetizationEntry,
    rank_monetization_entries,
)


def entry(capability_id, status, evidence=()):
    return MonetizationEntry(
        capability_id=capability_id,
        capability_name=capability_id,
        offer="validated service",
        target_customer="customer",
        acquisition_channel="direct",
        delivery_evidence="artifact",
        cost_model="tracked",
        status=status,
        realized_revenue=100.0 if status in {"REVENUE_REALIZED", "PROFIT_VERIFIED"} else 0.0,
        verified_costs=20.0 if status == "PROFIT_VERIFIED" else 0.0,
        evidence_refs=list(evidence),
    )


class MonetizationRegistryTests(unittest.TestCase):
    def test_defined_path_is_not_revenue(self):
        record = entry("cinematic-factory", "MONETIZATION_PATH_DEFINED").to_record()
        self.assertEqual(record["status"], "MONETIZATION_PATH_DEFINED")
        self.assertEqual(record["realized_revenue"], 0.0)

    def test_profit_requires_realized_revenue(self):
        with self.assertRaises(ValueError):
            entry("api", "PROFIT_VERIFIED").to_record()

    def test_rank_uses_commercial_state_and_evidence(self):
        records = rank_monetization_entries(
            [
                entry("a", "CUSTOMER_VALIDATED", ["customer:1"]),
                entry("b", "REVENUE_REALIZED", ["payment:1"]),
                entry("c", "PROFIT_VERIFIED", ["payment:2", "cost:2"]),
            ]
        )
        self.assertEqual(records[0]["capability_id"], "c")
        self.assertEqual(records[-1]["capability_id"], "a")

    def test_financial_side_effects_are_disabled(self):
        record = entry("mining-intelligence", "PAYMENT_VERIFIED").to_record()
        self.assertFalse(record["automatic_purchase"])
        self.assertFalse(record["automatic_withdrawal"])
        self.assertFalse(record["funds_moved_by_brain"])


if __name__ == "__main__":
    unittest.main()
