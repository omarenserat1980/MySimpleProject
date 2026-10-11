#!/usr/bin/env python3
"""Static regression tests preventing recurrence of missing execution-contract wiring."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "brain-windows-real-boot.yml"
GATE = ROOT / "brain_v12" / "brain" / "windows_real_boot_closed_loop_gate.py"
FETCHER = ROOT / "brain_v12" / "brain" / "fetch_windows_execution_contract.py"


class WindowsContractWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")
        cls.gate = GATE.read_text(encoding="utf-8")
        cls.fetcher = FETCHER.read_text(encoding="utf-8")

    def test_contract_destination_is_explicitly_wired(self):
        self.assertIn("BRAIN_WINDOWS_EXECUTION_CONTRACT_FILE: ${{ github.workspace }}/windows-execution-contract.json", self.workflow)
        self.assertIn('os.environ.get("BRAIN_WINDOWS_EXECUTION_CONTRACT_FILE"', self.gate)
        self.assertIn('os.environ.get("BRAIN_WINDOWS_EXECUTION_CONTRACT_FILE"', self.fetcher)

    def test_contract_is_fetched_before_gate(self):
        fetch = self.workflow.find("- name: Fetch short-lived contract from Brain Control Plane")
        gate = self.workflow.find("- name: Verify Brain closed-loop execution contract")
        self.assertGreaterEqual(fetch, 0, "workflow must include the protected contract fetch step")
        self.assertGreater(gate, fetch, "contract fetch must precede contract verification")
        self.assertIn("python3 brain_v12/brain/fetch_windows_execution_contract.py", self.workflow[fetch:gate])
        self.assertIn("python3 brain_v12/brain/windows_real_boot_closed_loop_gate.py", self.workflow[gate:])

    def test_gate_requires_signature_and_expiry(self):
        self.assertIn("verify_contract_signature", self.gate)
        self.assertIn("WINDOWS_EXECUTION_CONTRACT_AUTHORITY_SIGNATURE_REQUIRED", self.gate)
        self.assertIn("WINDOWS_EXECUTION_CONTRACT_EXPIRED", self.gate)
        self.assertIn("WINDOWS_EXECUTION_CONTRACT_SOURCE_COMMIT_MISMATCH", self.gate)

    def test_six_secrets_are_preflighted_without_printing_values(self):
        names = (
            "BRAIN_CLOUD_EXECUTOR_REGISTRY_URL",
            "BRAIN_CLOUD_EXECUTOR_TOKEN",
            "BRAIN_CLOUD_EXECUTOR_ATTESTATION_PUBLIC_KEY_B64",
            "BRAIN_AUTHORITY_PUBLIC_KEY_B64",
            "BRAIN_WINDOWS_CONTROL_PLANE_URL",
            "BRAIN_WINDOWS_CONTRACT_DELIVERY_KEY",
        )
        preflight = self.workflow.split("- name: Preflight all protected Windows boot secrets", 1)[1].split("- name:", 1)[0]
        for name in names:
            self.assertIn(name, preflight)
        self.assertIn("required protected environment secret is empty", preflight)
        self.assertNotIn('echo "$BRAIN_WINDOWS_CONTRACT_DELIVERY_KEY"', preflight)


if __name__ == "__main__":
    unittest.main(verbosity=2)
