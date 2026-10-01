import unittest

from brain_v12.self_healing.generator_registry import (
    SUPPORTED_GENERATORS,
    is_supported,
    supported_candidates,
)


class GeneratorRegistryTests(unittest.TestCase):
    def test_unknown_candidate_is_not_supported(self):
        self.assertFalse(is_supported("unknown-future-generator"))

    def test_known_generator_is_explicit(self):
        self.assertIn("package-invocation-consistency", SUPPORTED_GENERATORS)

    def test_filter_only_returns_registered_candidates(self):
        candidates = [
            {"id": "package-invocation-consistency"},
            {"id": "unknown-future-generator"},
        ]
        self.assertEqual(
            supported_candidates(candidates),
            [{"id": "package-invocation-consistency"}],
        )


if __name__ == "__main__":
    unittest.main()
