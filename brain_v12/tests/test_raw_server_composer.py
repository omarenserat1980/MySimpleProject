import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from brain_v12.raw_server.composer import RawServerComposer, StageFailure


class RawServerComposerTests(unittest.TestCase):
    def test_stages_are_written_and_integrated_in_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            composer = RawServerComposer(tmp)
            with patch("brain_v12.raw_server.composer._total_memory_bytes", return_value=8 * 1024**3), patch(
                "brain_v12.raw_server.composer._available_memory_bytes", return_value=4 * 1024**3
            ):
                manifest = composer.build()
            self.assertEqual(manifest["server"]["readiness"], "READY_FOR_REVIEW")
            self.assertFalse(manifest["server"]["provisioned"])
            self.assertEqual(list(manifest["stages"]), composer.ORDER)
            for stage in composer.ORDER:
                self.assertTrue((Path(tmp) / "components" / f"{stage}.json").exists())
                self.assertEqual(manifest["stages"][stage]["status"], "PASS")
            self.assertTrue((Path(tmp) / "evidence" / "final.gate.json").exists())

    def test_ram_target_over_safe_cap_stops_before_cpu(self):
        with tempfile.TemporaryDirectory() as tmp:
            composer = RawServerComposer(tmp, target_ram_gb=2)
            with patch("brain_v12.raw_server.composer._total_memory_bytes", return_value=8 * 1024**3), patch(
                "brain_v12.raw_server.composer._available_memory_bytes", return_value=4 * 1024**3
            ):
                with self.assertRaises(StageFailure):
                    composer.build()
            self.assertTrue((Path(tmp) / "evidence" / "memory_foundation.gate.json").exists())
            ram_gate = json.loads((Path(tmp) / "evidence" / "ram_pool.gate.json").read_text())
            self.assertEqual(ram_gate["status"], "FAIL")
            self.assertFalse((Path(tmp) / "components" / "cpu_pool.json").exists())

    def test_no_real_resource_allocation_or_cloud_provisioning(self):
        with tempfile.TemporaryDirectory() as tmp:
            composer = RawServerComposer(tmp)
            with patch("brain_v12.raw_server.composer._total_memory_bytes", return_value=8 * 1024**3), patch(
                "brain_v12.raw_server.composer._available_memory_bytes", return_value=4 * 1024**3
            ):
                manifest = composer.build()
            self.assertFalse(manifest["server"]["provisioned"])
            ram = json.loads((Path(tmp) / "components" / "ram_pool.json").read_text())
            security = json.loads((Path(tmp) / "components" / "security_baseline.json").read_text())
            self.assertFalse(ram["allocated"])
            self.assertFalse(ram["reserved"])
            self.assertFalse(security["cloud_provisioning"])


if __name__ == "__main__":
    unittest.main()
