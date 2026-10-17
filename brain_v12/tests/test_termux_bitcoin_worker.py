import contextlib
import io
import os
import unittest
from unittest.mock import patch

from brain_v12.brain.termux_bitcoin_worker import (
    build_command, validate_pool_url, _positive_int, parse_miner_line, main,
    supervisor_exit_code, is_cpu_thermal_zone_type,
)


class TermuxBitcoinWorkerTests(unittest.TestCase):
    def test_only_cpu_related_thermal_zones_are_accepted(self):
        for zone_type in ("cpu-thermal", "CPU0", "soc_thermal", "gpu-therm", "package"):
            with self.subTest(zone_type=zone_type):
                self.assertTrue(is_cpu_thermal_zone_type(zone_type))
        for zone_type in ("battery", "modem-therm", "skin", "usb", "tsens_tz_sensor0", "unknown"):
            with self.subTest(zone_type=zone_type):
                self.assertFalse(is_cpu_thermal_zone_type(zone_type))

    def test_expected_duration_limit_is_success_even_when_terminated_by_signal(self):
        self.assertEqual(supervisor_exit_code("duration_limit", -15), 0)
        self.assertEqual(supervisor_exit_code("duration_limit", 0), 0)

    def test_unexpected_exit_and_thermal_stop_are_not_success(self):
        self.assertEqual(supervisor_exit_code("process_exit", 0), 1)
        self.assertEqual(supervisor_exit_code("thermal_limit", -15), 1)
        self.assertEqual(supervisor_exit_code("thermal_sensor_lost", -15), 1)
        self.assertEqual(supervisor_exit_code("user_interrupt", 130), 130)

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

    def _run_main_captured(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main()
        return code, output.getvalue()

    def test_live_mining_is_blocked_without_explicit_opt_in(self):
        with patch.dict(os.environ, {}, clear=True), patch(
            "brain_v12.brain.termux_bitcoin_worker.subprocess.Popen"
        ) as popen:
            code, output = self._run_main_captured()
        self.assertEqual(code, 2)
        self.assertIn("BLOCKED_OPT_IN_REQUIRED", output)
        popen.assert_not_called()

    def test_live_mining_is_blocked_in_github_actions_even_with_opt_in(self):
        env = {"BRAIN_ENABLE_LIVE_MINING": "YES", "GITHUB_ACTIONS": "true"}
        with patch.dict(os.environ, env, clear=True), patch(
            "brain_v12.brain.termux_bitcoin_worker.subprocess.Popen"
        ) as popen:
            code, output = self._run_main_captured()
        self.assertEqual(code, 2)
        self.assertIn("BLOCKED_CI_ENVIRONMENT", output)
        popen.assert_not_called()

    def test_live_mining_is_blocked_without_thermal_sensor(self):
        env = {
            "BRAIN_ENABLE_LIVE_MINING": "YES",
            "TERMUX_VERSION": "test",
            "BRAIN_MINING_POOL_URL": "stratum+tcp://pool.example:3333",
            "BRAIN_MINING_WORKER": "wallet.worker1",
            "BRAIN_CPUMINER_BIN": "/usr/bin/cpuminer",
        }
        with patch.dict(os.environ, env, clear=True), patch(
            "brain_v12.brain.termux_bitcoin_worker.read_max_temperature_c",
            return_value=None,
        ), patch("brain_v12.brain.termux_bitcoin_worker.subprocess.Popen") as popen:
            code, output = self._run_main_captured()
        self.assertEqual(code, 2)
        self.assertIn("BLOCKED_THERMAL_SENSOR_UNAVAILABLE", output)
        popen.assert_not_called()

    def test_live_mining_is_blocked_outside_termux(self):
        env = {"BRAIN_ENABLE_LIVE_MINING": "YES"}
        with patch.dict(os.environ, env, clear=True), patch(
            "brain_v12.brain.termux_bitcoin_worker.Path.is_dir", return_value=False
        ), patch("brain_v12.brain.termux_bitcoin_worker.subprocess.Popen") as popen:
            code, output = self._run_main_captured()
        self.assertEqual(code, 2)
        self.assertIn("BLOCKED_NOT_TERMUX", output)
        popen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
