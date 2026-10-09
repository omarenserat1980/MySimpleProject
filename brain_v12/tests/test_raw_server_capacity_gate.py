import unittest
from datetime import datetime, timedelta, timezone

from brain_v12.raw_server.capacity_gate import evaluate_capacity


class CapacityGateTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)
        self.captured = (self.now - timedelta(seconds=5)).isoformat()

    def decide(self, **overrides):
        args = {
            "available_bytes": 4 * 1024**3,
            "host_reserve_bytes": 2 * 1024**3,
            "existing_commitments_bytes": 256 * 1024**2,
            "requested_startup_bytes": 1 * 1024**3,
            "telemetry_captured_at": self.captured,
            "now": self.now,
        }
        args.update(overrides)
        return evaluate_capacity(**args)

    def test_allows_only_when_fresh_telemetry_and_budget_fit(self):
        result = self.decide()
        self.assertEqual(result.status, "ALLOW")
        self.assertEqual(result.safe_budget_bytes, 4 * 1024**3 - 2 * 1024**3 - 256 * 1024**2)

    def test_blocks_when_memory_budget_is_insufficient(self):
        result = self.decide(requested_startup_bytes=2 * 1024**3)
        self.assertEqual(result.status, "BLOCKED")
        self.assertIn("exceeds the safe available budget", " ".join(result.reasons))

    def test_blocks_stale_or_unknown_telemetry(self):
        stale = (self.now - timedelta(seconds=61)).isoformat()
        self.assertEqual(self.decide(telemetry_captured_at=stale).status, "BLOCKED")
        self.assertEqual(self.decide(available_bytes=None).status, "BLOCKED")

    def test_blocks_naive_timestamp_and_negative_values(self):
        self.assertEqual(self.decide(telemetry_captured_at="2026-10-10T11:59:00").status, "BLOCKED")
        self.assertEqual(self.decide(host_reserve_bytes=-1).status, "BLOCKED")

    def test_never_claims_to_reserve_or_allocate_resources(self):
        result = self.decide().to_dict()
        self.assertEqual(result["status"], "ALLOW")
        self.assertNotIn("allocated", result)
        self.assertNotIn("reserved", result)


if __name__ == "__main__":
    unittest.main()
