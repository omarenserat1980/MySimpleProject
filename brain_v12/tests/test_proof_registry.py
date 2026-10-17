import unittest
from datetime import datetime, timezone

from brain_v12.brain.proof_registry import GateDefinition, ProofGateRegistry


NOW = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)


class ProofGateRegistryTests(unittest.TestCase):
    def test_default_registry_keeps_revenue_and_manufacture_separate(self):
        registry = ProofGateRegistry()
        gates = {item["gate_id"]: item for item in registry.list_gates()}
        self.assertIn("provider_payout", gates["revenue_realized"]["required_proof_types"])
        self.assertIn("blockchain_confirmation", gates["revenue_realized"]["required_proof_types"])
        self.assertEqual(gates["silicon_manufacture"]["required_proof_types"], ["manufacturing_confirmation"])
        self.assertNotEqual(gates["asic_gdsii"]["gate_id"], gates["silicon_manufacture"]["gate_id"])

    def test_no_evidence_leaves_live_mining_blocked(self):
        result = ProofGateRegistry().evaluate("bitcoin_mining_live", [], now=NOW)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["missing_proof_types"], ["pool_connection", "observed_hashrate", "accepted_share"])

    def test_unknown_gate_is_unknown_not_pass(self):
        result = ProofGateRegistry().evaluate("not_registered", [], now=NOW)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["reason"], "UNKNOWN_GATE_ID")

    def test_duplicate_gate_ids_are_rejected(self):
        definition = GateDefinition("duplicate", ("proof",), 60)
        with self.assertRaises(ValueError):
            ProofGateRegistry((definition, definition))

    def test_registry_delegates_revision_check_to_engine(self):
        registry = ProofGateRegistry((GateDefinition("one", ("runtime_health",), 300),))
        record = {
            "evidence_id": "ev-one",
            "proof_type": "runtime_health",
            "source_type": "runtime_probe",
            "observed_at": NOW.isoformat(),
            "status": "VERIFIED",
            "environment": "production",
            "commit_sha": "wrong",
        }
        result = registry.evaluate("one", [record], expected_commit_sha="expected", now=NOW)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["rejected_evidence"][0]["reason"], "COMMIT_MISMATCH")


if __name__ == "__main__":
    unittest.main()
