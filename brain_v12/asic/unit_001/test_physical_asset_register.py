import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("physical_asset_register.py")
spec = importlib.util.spec_from_file_location("physical_asset_register", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PhysicalAssetRegisterTests(unittest.TestCase):
    def test_empty_register_is_valid_and_has_zero_physical_assets(self):
        report = module.validate_register({"budget_jod": 0, "items": []})
        self.assertTrue(report["valid"])
        self.assertEqual(report["physical_inventory_count_verified"], 0)
        self.assertFalse(report["financial_execution_enabled"])

    def test_simulated_item_cannot_count_as_physical(self):
        data = {"budget_jod": 0, "items": [{
            "internal_asset_id": "BRAIN-ASIC-001-U1",
            "evidence_class": "SIMULATED",
            "counts_as_physical_inventory": True
        }]}
        report = module.validate_register(data)
        self.assertFalse(report["valid"])
        self.assertTrue(any("cannot count as physical inventory" in e for e in report["errors"]))

    def test_physical_item_requires_receipt_date_and_photos(self):
        data = {"budget_jod": 0, "items": [{
            "internal_asset_id": "BRAIN-ASIC-001-U1",
            "evidence_class": "PHYSICAL_OBSERVED",
            "evidence": {"received_date": "2026-10-17", "photo_urls": ["https://example.invalid/item.jpg"]}
        }]}
        report = module.validate_register(data)
        self.assertTrue(report["valid"])
        self.assertEqual(report["physical_inventory_count_verified"], 1)

    def test_market_value_requires_real_asset_and_sources(self):
        data = {"budget_jod": 0, "items": [{
            "internal_asset_id": "BRAIN-ASIC-001-U1",
            "evidence_class": "SIMULATED",
            "market_valuation": {"amount": 50, "currency": "USD", "valuation_date": "2026-10-17", "source_urls": ["https://example.invalid"], "condition": "used"}
        }]}
        report = module.validate_register(data)
        self.assertFalse(report["valid"])
        self.assertTrue(any("simulated/unreceived assets" in e for e in report["errors"]))

    def test_realized_sale_requires_sold_and_paid_evidence(self):
        data = {"budget_jod": 0, "items": [{
            "internal_asset_id": "BRAIN-ASIC-001-U1",
            "evidence_class": "PHYSICAL_OBSERVED",
            "evidence": {"received_date": "2026-10-17", "photo_urls": ["https://example.invalid/item.jpg"]},
            "sale_price_realized": 99
        }]}
        report = module.validate_register(data)
        self.assertFalse(report["valid"])
        self.assertTrue(any("realized sale requires SOLD_AND_PAID" in e for e in report["errors"]))


if __name__ == "__main__":
    unittest.main()
