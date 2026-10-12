import json
import tempfile
import unittest
from pathlib import Path

from brain_v12.virtual_hardware.arkan_persistence import (
    load_arkan_checkpoint, save_arkan_checkpoint,
)
from brain_v12.virtual_hardware.arkan_provisioner import ARKAN_ID, provision_arkan


class ArkanPersistenceTests(unittest.TestCase):
    def test_checkpoint_round_trip_is_durable_and_identity_bound(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            machine = provision_arkan(root / "identity.json")["machine"]
            machine.execute([("MOVI", 0, 17), ("OUT", 0), ("HALT",)], max_cycles=10)
            checkpoint = machine.checkpoint()
            saved = save_arkan_checkpoint(checkpoint, root / "checkpoint.json")
            loaded = load_arkan_checkpoint(root / "checkpoint.json")
            self.assertTrue(saved["ok"])
            self.assertEqual(loaded["device_id"], ARKAN_ID)
            self.assertEqual(loaded["checkpoint"], checkpoint)
            self.assertFalse((root / "checkpoint.json").stat().st_mode & 0o077)

    def test_missing_checkpoint_is_not_synthesized(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(FileNotFoundError, "ARKAN_CHECKPOINT_NOT_FOUND"):
                load_arkan_checkpoint(Path(tmp) / "missing.json")

    def test_modified_checkpoint_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "checkpoint.json"
            machine = provision_arkan(Path(tmp) / "identity.json")["machine"]
            save_arkan_checkpoint(machine.checkpoint(), path)
            envelope = json.loads(path.read_text(encoding="utf-8"))
            envelope["checkpoint"]["boot_count"] = 999
            path.write_text(json.dumps(envelope), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "ARKAN_CHECKPOINT_ENVELOPE_CHECKSUM_INVALID"):
                load_arkan_checkpoint(path)

    def test_wrong_machine_identity_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "ARKAN_CHECKPOINT_MACHINE_ID_INVALID"):
            save_arkan_checkpoint({"machine_id": "physical-arkan"})


if __name__ == "__main__":
    unittest.main()
