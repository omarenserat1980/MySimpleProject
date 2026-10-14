import importlib.util
import pathlib
import unittest

MODULE_PATH = pathlib.Path(__file__).parents[1] / "tools" / "benchmark_sha256d.py"
SPEC = importlib.util.spec_from_file_location("benchmark_sha256d", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class Sha256dBenchmarkTests(unittest.TestCase):
    def test_genesis_known_nonce_matches_known_raw_digest(self):
        header = MODULE.HEADER_PREFIX + (0x7C2BAC1D).to_bytes(4, "little")
        self.assertEqual(len(header), 80)
        self.assertEqual(
            MODULE.double_sha256(header).hex(),
            "6fe28c0ab6f1b372c1a6a246ae63f74f"
            "931e8365e15a089c68d6190000000000",
        )

    def test_benchmark_reports_software_only_and_count(self):
        result = MODULE.benchmark(3)
        self.assertEqual(result["hashes_per_sample"], 3)
        self.assertEqual(result["repeats"], 3)
        self.assertEqual(len(result["samples"]), 3)
        self.assertGreater(result["median_hashes_per_second"], 0)
        self.assertEqual(result["execution"], "host_cpu_software")
        self.assertFalse(result["is_live_mining"])
        self.assertFalse(result["is_rtl_or_asic_measurement"])
        self.assertEqual(len(result["last_digest_hex"]), 64)

    def test_rejects_invalid_count(self):
        with self.assertRaises(ValueError):
            MODULE.benchmark(0)

    def test_rejects_invalid_repeat_count(self):
        with self.assertRaises(ValueError):
            MODULE.benchmark(1, 10)


if __name__ == "__main__":
    unittest.main()
