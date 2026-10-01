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

    def test_contract_declares_verification_and_scope(self):
        spec = SUPPORTED_GENERATORS["package-invocation-consistency"]
        self.assertEqual(spec["max_changed_files"], 1)
        self.assertIn("gate", spec["verification"])
        self.assertTrue(spec["roots"])

    def test_candidate_path_must_match_contract_scope(self):
        from brain_v12.self_healing.generator_registry import candidate_valid
        self.assertTrue(candidate_valid({
            "id": "package-invocation-consistency",
            "file": "brain_v12/self_healing/review_loop.py",
        }))
        self.assertFalse(candidate_valid({
            "id": "package-invocation-consistency",
            "file": "../outside.py",
        }))

    def test_filter_only_returns_registered_candidates(self):
        candidates = [
            {"id": "package-invocation-consistency", "file": "brain_v12/self_healing/review_loop.py"},
            {"id": "unknown-future-generator", "file": "brain_v12/self_healing/review_loop.py"},
        ]
        self.assertEqual(
            supported_candidates(candidates),
            [{"id": "package-invocation-consistency"}],
        )


if __name__ == "__main__":
    unittest.main()
