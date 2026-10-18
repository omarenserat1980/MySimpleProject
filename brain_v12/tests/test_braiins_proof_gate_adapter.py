from __future__ import annotations

import unittest
from datetime import datetime, timezone

from brain_v12.brain.braiins_proof_gate_adapter import braiins_telemetry_to_proof_records
from brain_v12.brain.proof_registry import ProofGateRegistry


def live_result(**overrides):
    result = {
        "ok": True,
        "status": "POOL_ACTIVITY_OBSERVED",
        "pool_activity_verified": True,
        "pool_source_authenticated_over_https": True,
        "evidence_origin": "LIVE_HTTPS_RESPONSE",
        "proof_level": "INDEPENDENT_POOL_API_AGGREGATE_TELEMETRY",
        "pool_response_sha256": "a" * 64,
        "observed_at_utc": "2026-10-18T20:00:00Z",
        "worker_id": "account.worker-01",
        "hashrate_5m_provider_units": 12.5,
        "hashrate_unit": "Gh/s",
    }
    result.update(overrides)
    return result


class BraiinsProofGateAdapterTests(unittest.TestCase):
    def test_live_pool_aggregate_yields_only_connection_and_hashrate_proofs(self):
        records = braiins_telemetry_to_proof_records(live_result())
        self.assertEqual([item["proof_type"] for item in records], ["pool_connection", "observed_hashrate"])
        self.assertTrue(all(item["status"] == "VERIFIED" for item in records))
        self.assertTrue(all(item["source_type"] == "braiins_pool_readonly_api" for item in records))
        self.assertFalse(any(item["proof_type"] == "accepted_share" for item in records))
        self.assertFalse(any(item["proof_type"] in {"provider_payout", "blockchain_confirmation"} for item in records))

    def test_aggregate_telemetry_cannot_unlock_live_mining_gate(self):
        records = braiins_telemetry_to_proof_records(live_result())
        result = ProofGateRegistry().evaluate(
            "bitcoin_mining_live",
            records,
            now=datetime(2026, 10, 18, 20, 0, tzinfo=timezone.utc),
        )
        self.assertNotEqual(result["status"], "PASS")
        self.assertEqual(result["missing_proof_types"], ["accepted_share"])

    def test_test_fixture_and_blocked_snapshots_produce_no_evidence(self):
        self.assertEqual(braiins_telemetry_to_proof_records(live_result(
            status="TEST_FIXTURE_ONLY",
            pool_activity_verified=False,
            pool_source_authenticated_over_https=False,
            evidence_origin="INJECTED_TEST_FIXTURE",
            proof_level="SYNTHETIC_TEST_FIXTURE",
        )), [])
        self.assertEqual(braiins_telemetry_to_proof_records(live_result(ok=False, status="BLOCKED")), [])

    def test_malformed_provenance_or_metrics_produce_no_evidence(self):
        self.assertEqual(braiins_telemetry_to_proof_records(live_result(pool_response_sha256="bad")), [])
        self.assertEqual(braiins_telemetry_to_proof_records(live_result(observed_at_utc="")), [])
        self.assertEqual(braiins_telemetry_to_proof_records(live_result(worker_id="")), [])
        self.assertEqual(braiins_telemetry_to_proof_records(live_result(hashrate_5m_provider_units=True)), [])
        self.assertEqual(braiins_telemetry_to_proof_records(live_result(hashrate_5m_provider_units=0)), [])


if __name__ == "__main__":
    unittest.main()
