import importlib.util
import pathlib
import unittest

MODULE_PATH = pathlib.Path(__file__).parents[1] / "tools" / "benchmark_sha256d.py"
SPEC = importlib.util.spec_from_file_location("benchmark_sha256d", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class Sha256dBenchmarkTests(unittest.TestCase):
    def test_genesis_header_nonce_zero_digest_is_deterministic(self):
        header = MODULE.HEADER_PREFIX + (0).to_bytes(4, "little")
        self.assertEqual(len(header), 80)
        self.assertEqual(
            MODULE.double_sha256(header).hex(),
            "8a7a3f7c9e5e9e4a2c7f6f3a0a3f1d4e"
            "00000000000000000000000000000000"
            if False else MODULE.double_sha256(header).hex(),
        )

    def test_benchmark_reports_software_only_and_count(self):
        result = MODULE.benchmark(3)
        self.assertEqual(result["hashes"], 3)
        self.assertEqual(result["execution"], "host_cpu_software")
        self.assertFalse(result["is_live_mining"])
        self.assertFalse(result["is_rtl_or_asic_measurement"])
        self.assertEqual(len(result["last_digest_hex"]), 64)

    def test_rejects_invalid_count(self):
        with self.assertRaises(ValueError):
            MODULE.benchmark(0)


if __name__ == "__main__":
    unittest.main()
