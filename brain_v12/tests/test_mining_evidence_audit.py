import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from brain_v12.tools.mining_evidence_audit import audit_record, calculate_profit


class MiningEvidenceAuditTests(unittest.TestCase):
    def test_simulator_never_passes_as_real_mining(self):
        result = audit_record({"execution_mode": "SIMULATOR", "source_type": "SIMULATION"})
        self.assertFalse(result["real_mining_proven"])
        self.assertIn("SIMULATION_IS_NOT_REAL_MINING", result["failures"])

    def test_missing_evidence_is_unverified(self):
        result = audit_record({"execution_mode": "PHYSICAL_DEVICE"})
        self.assertEqual(result["status"], "UNVERIFIED")
        self.assertFalse(result["real_mining_proven"])

    def test_profit_counts_only_independently_verified_payouts(self):
        ledger = {
            "currency": "BTC",
            "verified_payouts": [{
                "transaction_id": "tx-001", "currency": "BTC",
                "amount": 0.001, "independently_verified": True
            }],
            "costs": {"electricity": 0.0002, "pool_fees": 0.0001}
        }
        result = calculate_profit(ledger)
        self.assertAlmostEqual(result["realized_net_profit"], 0.0007)
        self.assertEqual(result["status"], "CALCULATED_FROM_VERIFIED_INPUTS")

    def test_unverified_payout_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "UNVERIFIED_PAYOUT"):
            calculate_profit({
                "currency": "BTC",
                "verified_payouts": [{
                    "transaction_id": "tx-002", "currency": "BTC",
                    "amount": 1, "independently_verified": False
                }],
                "costs": {}
            })

    def test_duplicate_transaction_is_rejected(self):
        payout = {"transaction_id": "same", "currency": "BTC",
                  "amount": 0.1, "independently_verified": True}
        with self.assertRaisesRegex(ValueError, "DUPLICATE"):
            calculate_profit({"currency": "BTC", "verified_payouts": [payout, payout], "costs": {}})


if __name__ == "__main__":
    unittest.main()
