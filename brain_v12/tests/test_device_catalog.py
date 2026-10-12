"""Integrity and coverage tests for the virtual device catalog."""
import unittest
from brain_v12.virtual_hardware.device_catalog import (
    COMPONENT_CLASSES, DEVICE_FAMILIES, get_device_family,
    list_component_classes, list_device_families, validate_catalog,
)

class DeviceCatalogTests(unittest.TestCase):
    def test_integrity_and_coverage(self):
        report = validate_catalog()
        self.assertTrue(report["ok"], report)
        self.assertGreaterEqual(report["family_count"], 18)
        self.assertGreaterEqual(report["component_class_count"], 30)
        self.assertFalse(report["physical_hardware_required"])
        self.assertFalse(report["full_device_emulation_claimed"])

    def test_all_family_component_references_resolve(self):
        for family_id, family in DEVICE_FAMILIES.items():
            with self.subTest(family=family_id):
                resolved = get_device_family(family_id)
                self.assertEqual(len(family["components"]), len(resolved["component_inventory"]))
                self.assertTrue(all(c["component_id"] in COMPONENT_CLASSES for c in resolved["component_inventory"]))
                self.assertFalse(resolved["physical_hardware_required"])
                self.assertEqual(resolved["status"], "CATALOGED_NOT_FULLY_EMULATED")

    def test_expected_categories_and_filter(self):
        ids = {item["family_id"] for item in list_device_families()}
        self.assertTrue({"desktop_pc", "laptop", "server_workstation", "mobile_device", "game_console",
                         "network_appliance", "medical_device", "robot_industrial", "satellite_space",
                         "power_energy"} <= ids)
        self.assertTrue(all(x["category"] == "gaming" for x in list_device_families("gaming")))
        self.assertGreaterEqual(len(list_component_classes()), 30)

    def test_unknown_family_rejected(self):
        with self.assertRaisesRegex(ValueError, "UNKNOWN_DEVICE_FAMILY"):
            get_device_family("not-a-device")

    def test_returned_data_is_detached(self):
        family = get_device_family("laptop")
        family["components"].clear()
        self.assertTrue(DEVICE_FAMILIES["laptop"]["components"])

if __name__ == "__main__":
    unittest.main()
