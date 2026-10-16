"""Tests for fail-closed Braiins diagnostics classification."""
import unittest

from brain_v12.business.braiins_integration_diagnostics import classify_braiins_diagnostics


class BraiinsIntegrationDiagnosticsTests(unittest.TestCase):
    def test_missing_process_is_reported_first(self):
        result = classify_braiins_diagnostics({"miner_process_found": False})
        self.assertEqual(result["state"], "NO_MINER_PROCESS")
        self.assertFalse(result["real_mining_verified"])

    def test_dns_failure(self):
        result = classify_braiins_diagnostics({
            "miner_process_found": True, "dns_ok": False,
        })
        self.assertEqual(result["state"], "DNS_FAILURE")

    def test_tcp_failure(self):
        result = classify_braiins_diagnostics({
            "miner_process_found": True, "dns_ok": True, "tcp_ok": False,
        })
        self.assertEqual(result["state"], "STRATUM_TCP_UNREACHABLE")

    def test_zero_workers(self):
        result = classify_braiins_diagnostics({
            "miner_process_found": True, "dns_ok": True, "tcp_ok": True,
            "pool_worker_count": 0,
        })
        self.assertEqual(result["state"], "NO_POOL_WORKERS")

    def test_worker_without_hashrate_or_shares(self):
        result = classify_braiins_diagnostics({
            "miner_process_found": True, "dns_ok": True, "tcp_ok": True,
            "pool_worker_count": 1, "hashrate_hs": 0, "accepted_shares": 0,
        })
        self.assertEqual(result["state"], "WORKER_PRESENT_NO_HASHRATE_OR_SHARES")

    def test_accepted_shares_do_not_prove_payout(self):
        result = classify_braiins_diagnostics({
            "miner_process_found": True, "dns_ok": True, "tcp_ok": True,
            "pool_worker_count": 1, "hashrate_hs": 1000, "accepted_shares": 4,
        })
        self.assertEqual(result["state"], "POOL_ACCEPTED_SHARES_OBSERVED")
        self.assertFalse(result["real_mining_verified"])
        self.assertFalse(result["revenue_realized"])

    def test_invalid_values_fail_closed(self):
        result = classify_braiins_diagnostics({
            "miner_process_found": "yes", "pool_worker_count": -1,
            "hashrate_hs": -1, "accepted_shares": True,
        })
        self.assertEqual(result["state"], "INSUFFICIENT_EVIDENCE")
        self.assertFalse(result["real_mining_verified"])


if __name__ == "__main__":
    unittest.main()
