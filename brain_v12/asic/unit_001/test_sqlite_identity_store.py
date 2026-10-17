import json
import tempfile
import unittest
from pathlib import Path

from brain_v12.asic.unit_001.sqlite_identity_store import ASICIdentityStore


class ASICIdentityStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db = Path(self.temp_dir.name) / "brain" / "identity.sqlite3"
        self.store = ASICIdentityStore(self.db)
        self.store.init()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_init_and_health(self):
        result = self.store.health()
        self.assertEqual(result["status"], "SQLITE_READY")
        self.assertEqual(result["record_count"], 0)
        self.assertTrue(self.db.exists())

    def test_save_and_retrieve_incomplete_record_without_fabricating_identity(self):
        saved = self.store.save({})
        loaded = self.store.get("BRAIN-ASIC-001")
        self.assertEqual(saved, loaded)
        self.assertEqual(loaded["status"], "IDENTIFICATION_INCOMPLETE")
        self.assertIsNone(loaded["chip_part_number"])
        self.assertFalse(loaded["physical_hardware_verified"])
        self.assertFalse(loaded["mining_live_verified"])

    def test_upsert_keeps_one_current_record(self):
        self.store.save({"manufacturer": "Vendor A"})
        self.store.save({"manufacturer": "Vendor B"})
        rows = self.store.list_records()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["manufacturer"], "Vendor B")

    def test_live_mining_requires_evidence_references(self):
        record = self.store.save({
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

    def test_reject_non_object_input(self):
        with self.assertRaises(ValueError):
            self.store.save([])


if __name__ == "__main__":
    unittest.main()
