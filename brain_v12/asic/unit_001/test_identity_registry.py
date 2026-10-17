import unittest

from brain_v12.asic.unit_001.identity_registry import normalize_identity


class IdentityRegistryTests(unittest.TestCase):
    def test_empty_record_does_not_claim_hardware(self):
        record = normalize_identity({})
        self.assertEqual(record["brain_product_id"], "BRAIN-ASIC-001")
        self.assertFalse(record["identity_complete"])
        self.assertFalse(record["physical_hardware_verified"])
        self.assertFalse(record["connection_verified"])
        self.assertFalse(record["mining_live_verified"])
        self.assertEqual(record["status"], "IDENTIFICATION_INCOMPLETE")
        self.assertIsNone(record["chip_part_number"])

    def test_complete_identity_alone_does_not_verify_hardware(self):
        record = normalize_identity({
            "manufacturer": "Example Vendor",
            "device_model": "Board-X",
            "chip_part_number": "ASIC-X",
            "manufacturer_serial_number": "SERIAL-123",
            "datasheet_url": "https://example.invalid/datasheet",
        })
        self.assertTrue(record["identity_complete"])
        self.assertFalse(record["physical_hardware_verified"])

    def test_boolean_claims_without_evidence_do_not_verify_live_mining(self):
        record = normalize_identity({
            "manufacturer": "Example Vendor",
            "device_model": "Board-X",
            "chip_part_number": "ASIC-X",
            "manufacturer_serial_number": "SERIAL-123",
            "datasheet_url": "https://example.invalid/datasheet",
            "physical_device_seen": True,
            "manufacturer_identity_verified": True,
            "serial_number_verified": True,
            "connection_tested": True,
            "pool_accepted_share_verified": True,
        })
        self.assertFalse(record["physical_hardware_verified"])
        self.assertFalse(record["connection_verified"])
        self.assertFalse(record["mining_live_verified"])
        self.assertEqual(record["status"], "IDENTIFICATION_INCOMPLETE")

    def test_live_status_requires_evidence_at_each_gate(self):
        record = normalize_identity({
            "manufacturer": "Example Vendor",
            "device_model": "Board-X",
            "chip_part_number": "ASIC-X",
            "manufacturer_serial_number": "SERIAL-123",
            "datasheet_url": "https://example.invalid/datasheet",
            "physical_device_seen": True,
            "manufacturer_identity_verified": True,
            "serial_number_verified": True,
            "connection_tested": True,
            "pool_accepted_share_verified": True,
            "device_identity_evidence": "evidence/device-enumeration.txt",
            "photo_or_label_evidence": "evidence/board-label.jpg",
            "connection_test_evidence": "evidence/connection-test.json",
            "accepted_share_evidence": "evidence/pool-share.json",
        })
        self.assertTrue(record["physical_hardware_verified"])
        self.assertTrue(record["connection_verified"])
        self.assertTrue(record["mining_live_verified"])
        self.assertEqual(record["status"], "LIVE_MINING_EVIDENCE_VERIFIED")

    def test_invalid_usb_id_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_identity({"usb_vid": "not-hex"})

    def test_non_object_input_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_identity([])


if __name__ == "__main__":
    unittest.main()
