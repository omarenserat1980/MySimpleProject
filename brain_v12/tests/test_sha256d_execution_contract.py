"""Contract and RTL-adapter safety tests; external tools are never required."""
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from brain_v12.brain.sha256d_execution_contract import (
    make_layer_result, validate_layer_result, layer_status_snapshot,
)
from brain_v12.brain.sha256d_rtl_adapter import (
    _run_command, classify_simulation_result, normalize_cpu_benchmark, run_rtl_smoke, validate_nonce_range,
)


class Sha256dExecutionContractTests(unittest.TestCase):
    def test_pass_without_evidence_is_downgraded(self):
        result = make_layer_result(layer="rtl_simulator", status="PASS", evidence={})
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("PASS_WITHOUT_EVIDENCE", result["error_code"])
        self.assertTrue(validate_layer_result(result)["valid"])

    def test_digest_tampering_is_detected(self):
        result = make_layer_result(layer="cpu_reference", status="PASS", evidence={"hashes": 1})
        result["evidence"]["hashes"] = 2
        self.assertIn("EVIDENCE_DIGEST_MISMATCH", validate_layer_result(result)["failures"])

    def test_invalid_status_fails_closed(self):
        result = make_layer_result(layer="rtl_simulator", status="MAGIC_SUCCESS", evidence={"marker": True})
        self.assertEqual(result["status"], "FAIL")

    def test_arabic_status_snapshot_separates_external_gates(self):
        snapshot = layer_status_snapshot()
        self.assertIn("حالة طبقات SHA-256d", snapshot["title_ar"])
        self.assertFalse(snapshot["pool_connected"])
        self.assertFalse(snapshot["revenue_verified"])
        self.assertEqual(snapshot["layers"][1]["status"], "NOT_RUN")

    def test_cpu_benchmark_normalization_requires_evidence(self):
        good = normalize_cpu_benchmark({
            "mode": "LOCAL_BENCHMARK_ONLY", "hashes_completed": 12,
            "last_digest_hex": "a" * 64, "elapsed_seconds": 0.1, "hashrate_hs": 120.0,
        })
        bad = normalize_cpu_benchmark({"mode": "LOCAL_BENCHMARK_ONLY", "hashes_completed": 0})
        self.assertEqual(good["status"], "PASS")
        self.assertEqual(good["claims"]["pool_connected"], False)
        self.assertEqual(bad["status"], "FAIL")


class Sha256dRtlAdapterTests(unittest.TestCase):
    def test_nonce_range_limits_and_wrap_are_rejected(self):
        validate_nonce_range(0, 1)
        validate_nonce_range(0xFFFFFFFE, 2)
        for start, attempts in ((-1, 1), (0, 0), (0xFFFFFFFF, 2), (0, 1_000_001)):
            with self.subTest(start=start, attempts=attempts), self.assertRaises(ValueError):
                validate_nonce_range(start, attempts)

    def test_zero_exit_without_success_marker_is_not_pass(self):
        status, error, marker = classify_simulation_result(
            {"status": "PASS", "exit_code": 0}, "simulation ended without proof",
            "ALL_GENESIS_NONCE_SEARCH_TESTS_PASSED",
        )
        self.assertEqual(status, "FAIL")
        self.assertEqual(error, "SUCCESS_MARKER_MISSING")
        self.assertFalse(marker)

    def test_required_marker_and_zero_exit_are_both_required(self):
        status, error, marker = classify_simulation_result(
            {"status": "PASS", "exit_code": 0}, "ALL_GENESIS_NONCE_SEARCH_TESTS_PASSED",
            "ALL_GENESIS_NONCE_SEARCH_TESTS_PASSED",
        )
        self.assertEqual((status, error, marker), ("PASS", None, True))
        failed, _, _ = classify_simulation_result(
            {"status": "FAIL", "exit_code": 7}, "ALL_GENESIS_NONCE_SEARCH_TESTS_PASSED",
            "ALL_GENESIS_NONCE_SEARCH_TESTS_PASSED",
        )
        self.assertEqual(failed, "FAIL")

    def test_missing_tool_is_blocked(self):
        with patch("brain_v12.brain.sha256d_rtl_adapter.shutil.which", return_value=None):
            result = run_rtl_smoke()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("MISSING_TOOLS", result["error_code"])

    def test_unknown_testbench_is_blocked(self):
        result = run_rtl_smoke("arbitrary_shell_command")
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["error_code"], "RTL_CASE_NOT_ALLOWLISTED")

    def test_command_timeout_is_not_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = _run_command(
                [sys.executable, "-c", "import time; time.sleep(2)"],
                timeout_seconds=0.1, log_path=Path(tmp) / "timeout.log",
            )
        self.assertEqual(result["status"], "TIMEOUT")

    def test_cancelled_command_is_not_pass(self):
        event = threading.Event()
        event.set()
        with tempfile.TemporaryDirectory() as tmp:
            result = _run_command(
                [sys.executable, "-c", "import time; time.sleep(2)"],
                timeout_seconds=2, cancel_event=event,
                log_path=Path(tmp) / "cancel.log",
            )
        self.assertEqual(result["status"], "CANCELLED")

    def test_nonzero_tool_exit_is_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = _run_command(
                [sys.executable, "-c", "raise SystemExit(7)"],
                timeout_seconds=2, log_path=Path(tmp) / "fail.log",
            )
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["exit_code"], 7)


if __name__ == "__main__":
    unittest.main()
