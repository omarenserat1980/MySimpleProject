"""Unit tests for Public Pool readiness; no pool/network/miner is contacted."""
import unittest

from brain_v12.business.public_pool_readiness import assess_public_pool_readiness


class PublicPoolReadinessTests(unittest.TestCase):
    def test_missing_address_fails_closed(self):
        result = assess_public_pool_readiness({})
        self.assertEqual(result["status"], "BLOCKED_CONFIGURATION")
        self.assertFalse(result["payout_address_configured"])
        self.assertFalse(result["miner_started"])
        self.assertFalse(result["network_connection_attempted"])

    def test_address_is_never_returned(self):
        address = "bc1q" + "a" * 38
        result = assess_public_pool_readiness({
            "BRAIN_MINING_PAYOUT_ADDRESS": address,
            "BRAIN_MINING_WORKER_NAME": "brain-realme",
        })
        self.assertNotIn(address, repr(result))
        self.assertTrue(result["payout_address_configured"])

    def test_valid_shaped_config_is_not_claimed_as_mining(self):
        result = assess_public_pool_readiness({
            "BRAIN_MINING_PAYOUT_ADDRESS": "bc1q" + "a" * 38,
            "BRAIN_MINING_WORKER_NAME": "brain-realme",
        })
        self.assertEqual(result["status"], "READY_FOR_MANUAL_REVIEW")
        self.assertTrue(result["ready_for_manual_review"])
        self.assertFalse(result["accepted_shares_verified"])
        self.assertFalse(result["revenue_realized"])
        self.assertFalse(result["miner_started"])

    def test_invalid_worker_name_fails_closed(self):
        result = assess_public_pool_readiness({
            "BRAIN_MINING_PAYOUT_ADDRESS": "bc1q" + "a" * 38,
            "BRAIN_MINING_WORKER_NAME": "bad worker name",
        })
        self.assertEqual(result["status"], "BLOCKED_CONFIGURATION")
        self.assertFalse(result["worker_name_valid"])


if __name__ == "__main__":
    unittest.main()
