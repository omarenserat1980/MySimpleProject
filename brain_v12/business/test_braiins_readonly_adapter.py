import unittest

from brain_v12.business.braiins_readonly_adapter import (
    parse_braiins_payouts_response,
    parse_braiins_workers_response,
)


class TestBraiinsReadonlyAdapter(unittest.TestCase):
    def test_parses_documented_worker_response(self):
        result = parse_braiins_workers_response({"btc": {"workers": {
            "account.worker1": {
                "state": "ok", "last_share": 1542103204,
                "hash_rate_5m": 14977, "hash_rate_60m": 15302,
                "hash_rate_24h": 15351, "shares_5m": 90304,
                "shares_60m": 1125762, "shares_24h": 20945364,
            }
        }}})
        self.assertEqual(result[0]["worker_id"], "account.worker1")
        self.assertEqual(result[0]["telemetry"].hashrate_24h, 15351)
        self.assertEqual(result[0]["evidence"]["proof_level"], "MINING_EVIDENCE_ONLY")

    def test_parses_payout_without_realizing_revenue(self):
        result = parse_braiins_payouts_response({"onchain": [{
            "status": "confirmed", "amount_sats": 50000, "fee_sats": 1000,
            "destination": "bc1example", "tx_id": "tx-example",
            "requested_at_ts": 1721997284, "resolved_at_ts": 1721999584,
        }]})
        self.assertEqual(result[0]["tx_id"], "tx-example")
        self.assertEqual(result[0]["amount_sats"], 50000)
        self.assertEqual(result[0]["proof_level"], "PAYOUT_EVIDENCE_ONLY")
        self.assertFalse(result[0]["revenue_realized"])

    def test_rejects_malformed_workers_payload(self):
        with self.assertRaises(ValueError):
            parse_braiins_workers_response({"btc": {"workers": []}})

    def test_rejects_negative_payout(self):
        with self.assertRaises(ValueError):
            parse_braiins_payouts_response({"onchain": [{"status": "confirmed", "amount_sats": -1}]})


if __name__ == "__main__":
    unittest.main()
