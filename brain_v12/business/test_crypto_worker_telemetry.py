import unittest

from brain_v12.business.crypto_worker_telemetry import (
    evidence_from_telemetry,
    normalize_braiins_worker,
)


class TestCryptoWorkerTelemetry(unittest.TestCase):
    def test_normalizes_documented_braiins_worker(self):
        telemetry = normalize_braiins_worker(
            "account.worker1",
            {
                "state": "ok",
                "last_share": 1542103204,
                "hash_rate_5m": 14977,
                "hash_rate_60m": 15302,
                "hash_rate_24h": 15351,
                "shares_5m": 90304,
                "shares_60m": 1125762,
                "shares_24h": 20945364,
            },
        )
        self.assertEqual(telemetry.state, "ok")
        self.assertEqual(telemetry.hashrate_24h, 15351)
        self.assertEqual(telemetry.shares_24h, 20945364)

    def test_telemetry_is_not_revenue_proof(self):
        telemetry = normalize_braiins_worker(
            "account.worker1",
            {
                "state": "ok",
                "hash_rate_5m": 100,
                "hash_rate_60m": 100,
                "hash_rate_24h": 100,
                "shares_5m": 10,
                "shares_60m": 20,
                "shares_24h": 30,
            },
        )
        evidence = evidence_from_telemetry(telemetry)
        self.assertEqual(evidence["proof_level"], "MINING_EVIDENCE_ONLY")
        self.assertFalse(evidence["payout_verified"])
        self.assertFalse(evidence["revenue_realized"])

    def test_rejects_negative_metrics(self):
        with self.assertRaises(ValueError):
            normalize_braiins_worker(
                "account.worker1",
                {
                    "state": "ok",
                    "hash_rate_5m": -1,
                    "hash_rate_60m": 1,
                    "hash_rate_24h": 1,
                    "shares_5m": 1,
                    "shares_60m": 1,
                    "shares_24h": 1,
                },
            )


if __name__ == "__main__":
    unittest.main()
