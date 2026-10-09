from __future__ import annotations

import os
import time
import unittest

from brain_v12.brain.performance import ShortTTLCache, performance_cache_ttl


class PerformanceCacheTests(unittest.TestCase):
    def test_verified_value_is_reused_until_ttl(self) -> None:
        calls = 0

        def compute() -> dict[str, bool]:
            nonlocal calls
            calls += 1
            return {"verified": True}

        cache = ShortTTLCache(0.05)
        self.assertEqual(cache.get_or_compute("x", compute), {"verified": True})
        self.assertEqual(cache.get_or_compute("x", compute), {"verified": True})
        self.assertEqual(calls, 1)
        time.sleep(0.06)
        self.assertEqual(cache.get_or_compute("x", compute), {"verified": True})
        self.assertEqual(calls, 2)

    def test_failed_value_is_never_cached(self) -> None:
        calls = 0

        def compute() -> dict[str, bool]:
            nonlocal calls
            calls += 1
            return {"verified": False}

        cache = ShortTTLCache(10)
        cache.get_or_compute("x", compute, cacheable=lambda value: value["verified"])
        cache.get_or_compute("x", compute, cacheable=lambda value: value["verified"])
        self.assertEqual(calls, 2)

    def test_ttl_environment_is_bounded(self) -> None:
        old = os.environ.get("BRAIN_PREFLIGHT_CACHE_TTL_SECONDS")
        try:
            os.environ["BRAIN_PREFLIGHT_CACHE_TTL_SECONDS"] = "2"
            self.assertEqual(performance_cache_ttl(), 2.0)
            os.environ["BRAIN_PREFLIGHT_CACHE_TTL_SECONDS"] = "11"
            with self.assertRaises(RuntimeError):
                performance_cache_ttl()
        finally:
            if old is None:
                os.environ.pop("BRAIN_PREFLIGHT_CACHE_TTL_SECONDS", None)
            else:
                os.environ["BRAIN_PREFLIGHT_CACHE_TTL_SECONDS"] = old


if __name__ == "__main__":
    unittest.main()
