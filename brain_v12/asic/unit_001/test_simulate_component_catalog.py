"""Tests for the BRAIN-ASIC-001 simulated component catalog validator."""
import json
import unittest
from pathlib import Path

from simulate_component_catalog import DEFAULT_CATALOG, validate_catalog


class SimulatedCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads(DEFAULT_CATALOG.read_text(encoding="utf-8"))

    def test_catalog_has_components_and_unique_simulation_ids(self):
        report = validate_catalog(self.catalog)
        self.assertGreater(report["component_count"], 0)
        self.assertTrue(report["validation_passed"], report["errors_ar"])
        self.assertEqual(report["component_count"], report["unique_simulation_id_count"])

    def test_simulation_never_claims_real_manufacturing_or_assembly(self):
        report = validate_catalog(self.catalog)
        self.assertEqual(report["real_component_count_verified"], 0)
        self.assertEqual(report["physical_serial_numbers_verified"], 0)
        self.assertFalse(report["manufacturing_order_sent"])
        self.assertFalse(report["ready_for_assembly"])

    def test_validator_rejects_duplicate_simulation_ids(self):
        altered = json.loads(json.dumps(self.catalog))
        altered["components"][1]["serial_simulation_id"] = altered["components"][0]["serial_simulation_id"]
        report = validate_catalog(altered)
        self.assertFalse(report["validation_passed"])
        self.assertTrue(report["duplicate_simulation_ids"])

    def test_validator_rejects_records_claiming_real_hardware(self):
        altered = json.loads(json.dumps(self.catalog))
        altered["components"][0]["physical_manufacturing_verified"] = True
        report = validate_catalog(altered)
        self.assertFalse(report["validation_passed"])
        self.assertIn("U1", report["errors_ar"][0] if report["errors_ar"] else "")


if __name__ == "__main__":
    unittest.main()
