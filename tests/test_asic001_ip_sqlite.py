"""Tests for the ASIC-001 SQLite private-IP assignment registry."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from brain_v12.tools.asic001_ip_sqlite import ASICIPStore, validate_private_ipv4


class ASICIPStoreTests(unittest.TestCase):
    def test_rejects_public_and_invalid_addresses(self):
        for value in ("8.8.8.8", "not-an-ip", "127.0.0.1", "169.254.1.2", "::1"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_private_ipv4(value)

    def test_persists_known_private_ip_without_claiming_verification(self):
        with tempfile.TemporaryDirectory() as temp:
            store = ASICIPStore(Path(temp) / "asic.sqlite3")
            store.init()
            record = store.save("192.168.1.50")
            self.assertEqual(record["product_id"], "BRAIN-ASIC-001")
            self.assertEqual(record["ip_address"], "192.168.1.50")
            self.assertEqual(record["api_port"], 4028)
            self.assertEqual(record["connection_verified"], 0)
            self.assertEqual(record["live_mining_verified"], 0)
            self.assertEqual(store.get()["ip_address"], "192.168.1.50")

    def test_update_resets_verification_flags(self):
        with tempfile.TemporaryDirectory() as temp:
            store = ASICIPStore(Path(temp) / "asic.sqlite3")
            store.init()
            store.save("192.168.1.50")
            with store.connect() as conn:
                conn.execute(
                    "UPDATE asic_network_assignments SET connection_verified=1, live_mining_verified=1 "
                    "WHERE product_id='BRAIN-ASIC-001'"
                )
            updated = store.save("10.0.0.22")
            self.assertEqual(updated["ip_address"], "10.0.0.22")
            self.assertEqual(updated["connection_verified"], 0)
            self.assertEqual(updated["live_mining_verified"], 0)


if __name__ == "__main__":
    unittest.main()
