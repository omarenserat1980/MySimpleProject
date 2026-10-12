import unittest
from datetime import datetime, timedelta, timezone

from brain_v12.brain.canonical_indicators import (
    VerificationLevel,
    aggregate_required_indicators,
    build_indicator,
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

    def test_empty_aggregate_is_unknown(self):
        result = aggregate_required_indicators([])
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertFalse(result["healthy"])

    def test_blank_identity_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "INDICATOR_ID_SUBJECT_AND_SOURCE_REQUIRED"):
            self.make(subject_id=" ")


if __name__ == "__main__":
    unittest.main()
