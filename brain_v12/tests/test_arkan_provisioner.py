import json
import tempfile
import unittest
from pathlib import Path

from brain_v12.virtual_hardware.arkan_provisioner import (
    ARKAN_ID, arkan_status, provision_arkan, read_arkan_record,
)


class ArkanProvisionerTests(unittest.TestCase):
    def test_first_provisioning_creates_canonical_simulation_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "arkan.json"
            result = provision_arkan(path)
            record = result["record"]
            self.assertEqual(record["device_id"], ARKAN_ID)
            self.assertEqual(record["device_name"], "Arkan")
            self.assertEqual(record["readiness"], "SIMULATION_READY")
            self.assertTrue(result["machine"].powered)
            result["machine"].cpu.reset()
            workload = result["machine"].execute([("MOVI", 0, 42), ("OUT", 0), ("HALT",)], max_cycles=10)
            self.assertEqual(workload["output"], [42])
            self.assertEqual(workload["halted"], True)
            self.assertEqual(record["execution_backend"], "brain-simulator")
            self.assertFalse(record["claims"]["native_os_boot_verified"])
            self.assertEqual(record["os_target"]["installation_status"], "NOT_INSTALLED")
            self.assertIsNone(record["host_binding"])
            self.assertTrue(path.is_file())

    def test_repeated_provisioning_reconciles_one_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "arkan.json"
            first = provision_arkan(path)
            second = provision_arkan(path)
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(first["record"]["device_id"], second["record"]["device_id"])
            self.assertEqual(saved["device_id"], ARKAN_ID)
            self.assertEqual(saved["provisioning"]["created_at"], first["record"]["provisioning"]["created_at"])
            self.assertTrue(saved["provisioning"]["idempotent"])

    def test_wrong_machine_identity_is_rejected(self):
        from brain_v12.virtual_hardware.computer import VirtualComputer
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "ARKAN_MACHINE_ID_MISMATCH"):
                provision_arkan(Path(tmp) / "arkan.json", VirtualComputer(name="physical-arkan"))

    def test_status_does_not_invent_missing_identity_or_os_boot(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "missing.json"
            self.assertFalse(arkan_status(path)["exists"])
            provision_arkan(path)
            status = arkan_status(path)
            self.assertTrue(status["exists"])
            self.assertEqual(status["readiness"], "SIMULATION_READY")
            self.assertFalse(status["native_os_boot_verified"])
            self.assertFalse(status["runtime_state_persisted"])

    def test_registry_rejects_wrong_identity_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "arkan.json"
            path.write_text('{"device_id":"physical-arkan"}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "ARKAN_REGISTRY_IDENTITY_INVALID"):
                read_arkan_record(path)


if __name__ == "__main__":
    unittest.main()
