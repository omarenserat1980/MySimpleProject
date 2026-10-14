import unittest

from brain_v12.brain.termux_bitcoin_worker import (
    build_command, validate_pool_url, _positive_int, parse_miner_line,
)


class TermuxBitcoinWorkerTests(unittest.TestCase):
    def test_builds_sha256d_command_with_bounded_threads(self):
        command = build_command(
            "/usr/bin/cpuminer", "stratum+tcp://pool.example:3333",
            "wallet.worker1", 2,
        )
        self.assertEqual(command[1:3], ["-a", "sha256d"])
        self.assertIn("stratum+tcp://pool.example:3333", command)
        self.assertEqual(command[-2:], ["-t", "2"])
        self.assertNotIn("BRAIN_ENABLE_LIVE_MINING", command)

    def test_rejects_non_stratum_and_credential_bearing_urls(self):
        for url in (
            "https://pool.example:3333",
            "stratum+tcp://user:pass@pool.example:3333",
            "stratum+tcp://pool.example",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_pool_url(url)

    def test_thread_and_duration_values_are_bounded(self):
        self.assertEqual(_positive_int("1", "threads", 1, 2), 1)
        with self.assertRaises(ValueError):
            _positive_int("3", "threads", 1, 2)
        with self.assertRaises(ValueError):
            _positive_int("0", "duration", 60, 300)

    def test_rejects_unsafe_worker_name(self):
        with self.assertRaises(ValueError):
            build_command("cpuminer", "stratum+tcp://pool.example:3333", "wallet;rm -rf /", 1)

    def test_parses_miner_output_as_unverified_candidate_signals(self):
        counters = {
            "accepted_shares": 0,
            "rejected_or_stale_lines": 0,
            "authorization_message_seen": False,
            "last_reported_hashrate_hs": None,
            "hashrate_unit_source": None,
        }
        parse_miner_line("accepted: 1/1 (100.00%), 12.50 khash/s", counters)
        parse_miner_line("rejected: 1/2 (50.00%)", counters)
        parse_miner_line("Stratum authorization successful", counters)
        self.assertEqual(counters["accepted_shares"], 1)
        self.assertEqual(counters["rejected_or_stale_lines"], 1)
        self.assertTrue(counters["authorization_message_seen"])
        self.assertEqual(counters["last_reported_hashrate_hs"], 12500.0)
        self.assertEqual(counters["hashrate_unit_source"], "miner_stdout_stderr_unverified")


if __name__ == "__main__":
    unittest.main()
