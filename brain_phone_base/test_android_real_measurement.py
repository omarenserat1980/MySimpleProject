import json
import tempfile
import unittest
from pathlib import Path

from brain_phone_base.android_real_measurement import collect_measurement, write_evidence


class RealMeasurementTests(unittest.TestCase):
    def test_schema_and_safe_default_gates(self):
        result = collect_measurement()
        self.assertEqual(result["schema"], "brain-phone-base.real-measurement.v1")
        self.assertEqual(result["collection_mode"], "read_only_local")
        self.assertEqual(result["evidence"]["classification"], "local_measurement_unattested")
        self.assertEqual(result["evidence"]["independent_verification"], "not_performed")
        self.assertFalse(result["evidence"]["device_identity_verified"])
        self.assertFalse(result["node_gate"]["trusted"])
        self.assertFalse(result["node_gate"]["active"])
        self.assertFalse(result["node_gate"]["activation_allowed"])
        self.assertEqual(result["node_gate"]["manual_approval"], "not_granted")
        self.assertFalse(result["network_actions"]["measurement_uploaded"])
        self.assertFalse(result["network_actions"]["node_registered"])
        self.assertFalse(result["network_actions"]["mining_started"])
        self.assertFalse(result["network_actions"]["mining_pool_contacted"])

    def test_measurement_does_not_expose_unique_device_identifiers(self):
        result = collect_measurement()
        serialized = json.dumps(result).lower()
        for forbidden in ("imei", "android_id", "serial_number", "device_serial", "account_token"):
            self.assertNotIn(forbidden, serialized)

    def test_writes_parseable_local_json(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "evidence" / "measurement.json"
            result = write_evidence(target)
            parsed = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(parsed["measurement_id"], result["measurement_id"])
            self.assertTrue(target.is_file())
            self.assertIn("measurements", parsed)
            self.assertIn("measurement_sources", parsed)


if __name__ == "__main__":
    unittest.main()
