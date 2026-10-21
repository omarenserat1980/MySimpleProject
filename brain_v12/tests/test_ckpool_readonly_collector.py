from __future__ import annotations

import json
import unittest

from brain_v12.brain.ckpool_readonly_collector import (
    collect_ckpool_readonly,
    validate_btc_address,
)


class CKPoolReadonlyCollectorTests(unittest.TestCase):
    def test_parses_pool_stats_and_never_claims_revenue(self):
        def fake_fetch(url):
            assert url.endswith("/pool/pool.status")
            return '{"runtime":12,"Users":3,"Workers":4}\n{"hashrate1m":"2P"}\n'

        result = collect_ckpool_readonly(fetcher=fake_fetch, observed_at=123)
        self.assertTrue(result["pool_stats_available"])
        self.assertEqual(result["pool_stats"][0]["Workers"], 4)
        self.assertFalse(result["local_miner_started"])
        self.assertFalse(result["revenue_realized"])
        self.assertFalse(result["financial_execution_enabled"])
        self.assertEqual(result["observed_at_epoch"], 123)

    def test_user_stats_are_optional_and_address_not_echoed(self):
        address = "1BoatSLRHtKNngkdXEeobR76b53LETtpyT"
        urls = []
        def fake_fetch(url):
            urls.append(url)
            return '{"Workers":1,"hashrate1m":"0"}\n'
        result = collect_ckpool_readonly(address, fetcher=fake_fetch, observed_at=1)
        self.assertEqual(len(urls), 2)
        self.assertTrue(urls[1].endswith("/users/" + address))
        self.assertTrue(result["user_stats_available"])
        self.assertNotIn(address, json.dumps(result))
        self.assertFalse(result["local_share_acceptance_verified"])

    def test_rejects_invalid_address(self):
        with self.assertRaises(ValueError):
            validate_btc_address("../../etc/passwd")

    def test_pool_failure_is_fail_closed(self):
        def fail(_url):
            raise OSError("network unavailable")
        result = collect_ckpool_readonly(fetcher=fail, observed_at=1)
        self.assertFalse(result["pool_stats_available"])
        self.assertFalse(result["revenue_realized"])
        self.assertEqual(result["pool_error"], "OSError")


if __name__ == "__main__":
    unittest.main()
