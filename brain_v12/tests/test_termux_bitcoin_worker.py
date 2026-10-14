import unittest

from brain_v12.brain.termux_bitcoin_worker import build_command, validate_pool_url, _positive_int


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


if __name__ == "__main__":
    unittest.main()
