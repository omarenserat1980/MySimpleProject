import unittest
from unittest.mock import patch

from brain_v12.business.crypto_live_collector import collect_validated_btc_market_snapshot


class TestCryptoLiveCollector(unittest.TestCase):
    def test_public_snapshot_is_passed_through_freshness_gate(self):
        payloads = [
            {"USD": 100000.0},
            [{"avgHashrate": 700000000000000000000.0, "difficulty": 100000000000000000000.0}],
            {"usd_per_th_day": 0.05},
        ]
        with patch("brain_v12.business.crypto_live_collector._get_json", side_effect=payloads):
            snapshot = collect_validated_btc_market_snapshot()
        self.assertEqual(snapshot["data_quality"], "FRESH")
        self.assertEqual(snapshot["freshness_validation"]["freshness"], "FRESH")
        self.assertEqual(snapshot["freshness_validation"]["source"], snapshot["sources"]["hashprice"])
        self.assertFalse(snapshot["external_actions_enabled"])

    def test_invalid_public_payload_fails_closed(self):
        with patch("brain_v12.business.crypto_live_collector._get_json", return_value={"USD": 0}):
            with self.assertRaises(ValueError):
                collect_validated_btc_market_snapshot()


if __name__ == "__main__":
    unittest.main()
