import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "brain_asic_hosting_preflight.py"
SPEC = importlib.util.spec_from_file_location("brain_asic_hosting_preflight", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def valid_offer():
    return {
        "operator_legal_name": "Example Hosting Ltd",
        "facility_evidence_url": "https://example.invalid/facility",
        "public_pool_or_payout_evidence_url": "https://example.invalid/payout",
        "trial_terms_url": "https://example.invalid/terms",
        "trial_hashrate_ths": 50,
        "upfront_cost_usd": 0,
        "deposit_required_usd": 0,
        "recurring_cost_usd": 0,
        "withdrawal_fee_usd": 0,
        "activation_fee_usd": 0,
        "trial_rewards_withdrawable": True,
        "requires_paid_upgrade_to_withdraw": False,
        "requires_referrals_to_withdraw": False,
        "requires_wallet_seed_or_private_key": False,
        "physical_asic_disclosed": True,
        "external_wallet_payout_supported": True,
    }


class ASICHostingPreflightTests(unittest.TestCase):
    def test_valid_zero_cost_offer_only_enters_manual_review(self):
        result = MODULE.assess(valid_offer())
        self.assertEqual(result["status"], "NEEDS_MANUAL_REVIEW")
        self.assertFalse(result["eligible_for_automatic_activation"])
        self.assertFalse(result["safety"]["mining_started"])
        self.assertFalse(result["safety"]["withdrawal_verified"])

    def test_nonzero_recurring_cost_is_blocked(self):
        offer = valid_offer()
        offer["recurring_cost_usd"] = 0.01
        result = MODULE.assess(offer)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("NONZERO_RECURRING_COST_USD", result["errors"])

    def test_dashboard_rewards_not_withdrawable_are_blocked(self):
        offer = valid_offer()
        offer["trial_rewards_withdrawable"] = False
        result = MODULE.assess(offer)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("TRIAL_REWARDS_NOT_CONFIRMED_WITHDRAWABLE", result["errors"])

    def test_wallet_seed_request_is_blocked(self):
        offer = valid_offer()
        offer["requires_wallet_seed_or_private_key"] = True
        result = MODULE.assess(offer)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("WALLET_SECRET_REQUEST_RISK", result["errors"])

    def test_missing_physical_asic_disclosure_is_blocked(self):
        offer = valid_offer()
        offer["physical_asic_disclosed"] = False
        result = MODULE.assess(offer)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("PHYSICAL_ASIC_NOT_CONFIRMED", result["errors"])


if __name__ == "__main__":
    unittest.main()
