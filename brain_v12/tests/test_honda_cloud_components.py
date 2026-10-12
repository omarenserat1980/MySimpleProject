import unittest

from brain_v12.brain.honda_cloud_components import (
    HondaCloudPolicy,
    HondaVehicleProfile,
    evidence_digest,
    fingerprint_vin,
    plan_honda_cloud_components,
)


class HondaCloudComponentsTests(unittest.TestCase):
    def test_unverified_profile_stays_gated_and_cloud_off(self):
        plan = plan_honda_cloud_components(
            HondaVehicleProfile(profile_id="honda-primary"),
            HondaCloudPolicy(),
        )
        self.assertEqual(plan["next_gate"], "VERIFY_MODEL_AND_HEAD_UNIT")
        self.assertEqual(plan["components"]["evidence_vault"], "LOCAL_ONLY")
        self.assertFalse(plan["safety"]["cloud_provisioning_performed"])
        self.assertFalse(plan["safety"]["automatic_firmware_install"])

    def test_verified_nbox_cloud_plan_is_free_only_by_default(self):
        plan = plan_honda_cloud_components(
            HondaVehicleProfile(
                profile_id="honda-primary",
                model_code="HONDA_NBOX",
                model_year=2022,
                head_unit="unknown",
                verified=True,
            ),
            HondaCloudPolicy(cloud_sync_enabled=True),
        )
        self.assertEqual(plan["components"]["cloud_executor"], "ELIGIBLE_FREE_TIER_ONLY")
        self.assertEqual(plan["cost_ceiling_usd"], 0.0)
        self.assertFalse(plan["safety"]["remote_vehicle_commands"])

    def test_paid_budget_requires_explicit_approval(self):
        with self.assertRaises(ValueError):
            HondaCloudPolicy(max_cost_usd=1.0)

    def test_remote_vehicle_control_is_rejected(self):
        with self.assertRaises(ValueError):
            HondaCloudPolicy(allow_remote_vehicle_commands=True)

    def test_firmware_install_is_rejected(self):
        with self.assertRaises(ValueError):
            HondaCloudPolicy(allow_firmware_install=True)

    def test_vin_fingerprint_does_not_return_raw_vin(self):
        vin = "1HGCM82633A004352"
        digest = fingerprint_vin(vin)
        self.assertEqual(len(digest), 64)
        self.assertNotEqual(digest, vin)
        with self.assertRaises(ValueError):
            fingerprint_vin("NOT-A-VIN")

    def test_evidence_digest_is_order_independent(self):
        self.assertEqual(
            evidence_digest({"model": "N-BOX", "version": "1.0"}),
            evidence_digest({"version": "1.0", "model": "N-BOX"}),
        )


if __name__ == "__main__":
    unittest.main()
