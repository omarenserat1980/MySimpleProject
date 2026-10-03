"""Tests for the initial Brain monetization catalog."""
import unittest

from brain_v12.business.initial_monetization_catalog import (
    INITIAL_MONETIZATION_CATALOG,
    initial_catalog_records,
)


class InitialMonetizationCatalogTests(unittest.TestCase):
    def test_catalog_has_core_capabilities(self):
        ids = {entry.capability_id for entry in INITIAL_MONETIZATION_CATALOG}
        self.assertTrue({
            "mining-opportunity-intelligence",
            "cinematic-factory",
            "customer-portal-api",
            "brain-automation-services",
            "digital-commerce",
        }.issubset(ids))

    def test_catalog_starts_without_claiming_revenue(self):
        records = initial_catalog_records()
        self.assertTrue(records)
        for record in records:
            self.assertEqual(record["status"], "MONETIZATION_PATH_DEFINED")
            self.assertEqual(record["realized_revenue"], 0.0)

    def test_catalog_has_no_financial_side_effects(self):
        for record in initial_catalog_records():
            self.assertFalse(record["automatic_purchase"])
            self.assertFalse(record["automatic_contract"])
            self.assertFalse(record["automatic_withdrawal"])
            self.assertFalse(record["funds_moved_by_brain"])


if __name__ == "__main__":
    unittest.main()
