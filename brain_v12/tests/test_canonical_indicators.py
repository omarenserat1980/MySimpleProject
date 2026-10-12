import unittest
from datetime import datetime, timedelta, timezone

from brain_v12.brain.canonical_indicators import (
    VerificationLevel,
    aggregate_indicator_payloads,
    aggregate_required_indicators,
    build_indicator,
    indicators_for_fleet,
)


class CanonicalIndicatorTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 12, 12, 0, tzinfo=timezone.utc)

    def make(self, **overrides):
        values = {
            "indicator_id": "node.arkan.health",
            "subject_id": "arkan-virtual-01",
            "indicator_type": "health",
            "value": "healthy",
            "source": "brain-simulator",
            "verification_level": VerificationLevel.BACKEND_VERIFIED,
            "observed_at": self.now,
            "backend_id": "brain-simulator",
            "now": self.now,
        }
        values.update(overrides)
        return build_indicator(**values)

    def test_fresh_backend_evidence_is_verified_at_declared_level(self):
        item = self.make()
        self.assertEqual(item.status, "VERIFIED")
        self.assertEqual(item.subject_id, "arkan-virtual-01")
        self.assertEqual(item.verification_level, "BACKEND_VERIFIED")

    def test_missing_timestamp_is_unknown_not_green(self):
        item = self.make(observed_at=None)
        self.assertEqual(item.status, "UNKNOWN")
        self.assertEqual(item.error_code, "INDICATOR_OBSERVATION_MISSING_OR_INVALID")

    def test_stale_timestamp_is_stale(self):
        item = self.make(observed_at=self.now - timedelta(seconds=301))
        self.assertEqual(item.status, "STALE")

    def test_insufficient_evidence_level_is_unverified(self):
        item = self.make(
            verification_level=VerificationLevel.REGISTERED,
            required_level=VerificationLevel.BACKEND_VERIFIED,
        )
        self.assertEqual(item.status, "UNVERIFIED")

    def test_execution_level_requires_evidence_reference(self):
        item = self.make(verification_level=VerificationLevel.EXECUTION_VERIFIED)
        self.assertEqual(item.status, "UNVERIFIED")
        self.assertEqual(item.error_code, "INDICATOR_EVIDENCE_REFERENCE_REQUIRED")

    def test_execution_level_with_evidence_reference_passes(self):
        item = self.make(
            verification_level=VerificationLevel.EXECUTION_VERIFIED,
            evidence_refs=["sha256:abc123"],
        )
        self.assertEqual(item.status, "VERIFIED")
        self.assertEqual(item.public()["evidence_refs"], ["sha256:abc123"])

    def test_future_timestamp_is_unknown(self):
        item = self.make(observed_at=self.now + timedelta(minutes=2))
        self.assertEqual(item.status, "UNKNOWN")

    def test_aggregate_exposes_required_blockers(self):
        healthy = self.make()
        stale = self.make(indicator_id="node.disk", observed_at=self.now - timedelta(hours=1))
        result = aggregate_required_indicators([healthy, stale])
        self.assertEqual(result["status"], "DEGRADED")
        self.assertFalse(result["healthy"])
        self.assertEqual(result["verified_count"], 1)
        self.assertEqual(result["blockers"][0]["indicator_id"], "node.disk")

    def test_verified_but_failed_value_still_blocks_healthy_aggregate(self):
        failed = self.make(value="FAILED")
        result = aggregate_required_indicators([failed])
        self.assertEqual(failed.status, "VERIFIED")
        self.assertEqual(result["status"], "DEGRADED")
        self.assertFalse(result["healthy"])
        self.assertEqual(result["blockers"][0]["indicator_id"], "node.arkan.health")

    def test_verified_false_boolean_still_blocks_healthy_aggregate(self):
        failed = self.make(value=False)
        result = aggregate_required_indicators([failed])
        self.assertEqual(result["status"], "DEGRADED")
        self.assertFalse(result["healthy"])

    def test_empty_aggregate_is_unknown(self):
        result = aggregate_required_indicators([])
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertFalse(result["healthy"])

    def test_configured_but_not_running_is_a_health_blocker(self):
        item = self.make(value="CONFIGURED_NOT_RUNNING")
        result = aggregate_required_indicators([item])
        self.assertEqual(item.status, "VERIFIED")
        self.assertEqual(result["status"], "DEGRADED")
        self.assertFalse(result["healthy"])

    def test_public_payload_aggregate_reports_health_blockers(self):
        items = [
            self.make().public(),
            self.make(indicator_id="node.phone.readiness", value="PROFILE_REGISTERED_NOT_RUNNING").public(),
        ]
        result = aggregate_indicator_payloads(items)
        self.assertEqual(result["required_count"], 2)
        self.assertEqual(result["verified_count"], 2)
        self.assertEqual(result["status"], "DEGRADED")
        self.assertEqual(result["blockers"][0]["indicator_id"], "node.phone.readiness")

    def test_blank_identity_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "INDICATOR_ID_SUBJECT_AND_SOURCE_REQUIRED"):
            self.make(subject_id=" ")


    def test_fleet_adapter_keeps_missing_observation_unknown(self):
        fleet = {
            "fleet": [{
                "endpoint_id": "arkan-virtual-01",
                "role": "virtual_computer",
                "platform": "brain-simulator",
                "reality": "SIMULATED",
                "observed_state": "SIMULATION_READY",
                "physical_device_required": False,
            }]
        }
        items = indicators_for_fleet(fleet, now=self.now)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["status"], "UNKNOWN")
        self.assertIsNone(items[0]["observed_at"])

    def test_fleet_adapter_excludes_physical_and_non_simulated_rows(self):
        fleet = {"fleet": [
            {
                "endpoint_id": "arkan-host-sim-asus-vivobook",
                "role": "compute_host",
                "reality": "OBSERVED_DEVICE",
                "observed_state": "ONLINE",
            },
            {
                "endpoint_id": "phone-virtual-01",
                "role": "virtual_phone",
                "reality": "UNKNOWN",
                "observed_state": "ONLINE",
            },
        ]}
        self.assertEqual(indicators_for_fleet(fleet, now=self.now), [])

    def test_fleet_adapter_uses_backend_observation_time_when_present(self):
        fleet = {"fleet": [{
            "endpoint_id": "arkan-virtual-01",
            "role": "virtual_computer",
            "platform": "brain-simulator",
            "reality": "SIMULATED",
            "observed_state": "SIMULATION_READY",
            "observed_at": self.now.isoformat(),
            "physical_device_required": False,
        }]}
        items = indicators_for_fleet(fleet, now=self.now)
        self.assertEqual(items[0]["status"], "VERIFIED")
        self.assertEqual(items[0]["verification_level"], "REGISTERED")



    def test_fleet_adapter_excludes_explicitly_unselected_software_node(self):
        fleet = {"fleet": [
            {
                "endpoint_id": "arkan-virtual-01",
                "role": "virtual_computer",
                "platform": "brain-simulator",
                "reality": "SIMULATED",
                "indicator_selected": True,
                "observed_state": "CONFIGURED_NOT_RUNNING",
                "observed_at": self.now.isoformat(),
            },
            {
                "endpoint_id": "phone-virtual-01",
                "role": "virtual_phone",
                "platform": "brain-mobile-simulator",
                "reality": "SIMULATED",
                "indicator_selected": False,
                "observed_state": "PROFILE_REGISTERED_NOT_RUNNING",
                "observed_at": self.now.isoformat(),
            },
        ]}
        items = indicators_for_fleet(fleet, now=self.now)
        self.assertEqual([item["subject_id"] for item in items], ["arkan-virtual-01"])


if __name__ == "__main__":
    unittest.main()
