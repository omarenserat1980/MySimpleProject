import json
import tempfile
import unittest
from pathlib import Path

from brain_v12.tools.boot_readiness_triage import triage


class BootReadinessTriageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name, payload):
        p = self.root / name
        p.write_text(json.dumps(payload), encoding="utf-8")
        return str(p)

    def test_missing_evidence_blocks_all_gates(self):
        result = triage({})
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(result["ready"])
        self.assertEqual(len(result["blockers"]), 4)

    def test_all_verified_gates_ready_only_with_exact_boot_status(self):
        paths = {
            "contract_gate": self.write("contract.json", {"verified": True}),
            "executor_gate": self.write("executor.json", {"verified": True}),
            "runner_watch": self.write("runner.json", {
                "runner_online": True, "execution_probe": "PASS", "runtime_surface": "PASS"
            }),
            "boot_proof": self.write("boot.json", {"verified": True, "status": "WINDOWS_BOOT_VERIFIED"}),
        }
        result = triage(paths)
        self.assertEqual(result["status"], "READY")
        self.assertTrue(result["ready"])
        self.assertEqual(result["blockers"], [])

    def test_generic_verified_flag_does_not_prove_windows_boot(self):
        paths = {
            "contract_gate": self.write("contract.json", {"verified": True}),
            "executor_gate": self.write("executor.json", {"verified": True}),
            "runner_watch": self.write("runner.json", {
                "runner_online": True, "execution_probe": "PASS", "runtime_surface": "PASS"
            }),
            "boot_proof": self.write("boot.json", {"verified": True, "status": "INCOMPLETE"}),
        }
        result = triage(paths)
        self.assertFalse(result["ready"])
        self.assertEqual(result["gates"]["boot_proof"]["status"], "BLOCKED")

    def test_runner_online_without_execution_probe_is_blocked(self):
        paths = {
            "contract_gate": self.write("contract.json", {"verified": True}),
            "executor_gate": self.write("executor.json", {"verified": True}),
            "runner_watch": self.write("runner.json", {"runner_online": True}),
            "boot_proof": self.write("boot.json", {"verified": True, "status": "WINDOWS_BOOT_VERIFIED"}),
        }
        result = triage(paths)
        self.assertFalse(result["ready"])
        self.assertEqual(result["gates"]["runner"]["status"], "BLOCKED")

    def test_invalid_json_is_blocked(self):
        bad = self.root / "bad.json"
        bad.write_text("{", encoding="utf-8")
        result = triage({"contract_gate": str(bad)})
        self.assertEqual(result["gates"]["contract"]["reason"], "EVIDENCE_FILE_INVALID")


if __name__ == "__main__":
    unittest.main()
