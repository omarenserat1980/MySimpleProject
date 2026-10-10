import unittest

from brain_v12.brain.open_source_provider_registry import (
    assert_allowed_for_runtime,
    get_provider,
    list_providers,
)


class OpenSourceProviderRegistryTests(unittest.TestCase):
    def test_india_translation_provider(self):
        p = get_provider("india.ai4bharat.indictrans2")
        self.assertEqual(p.origin, "india")
        self.assertIn("translation", p.capabilities)

    def test_china_on_device_provider(self):
        p = get_provider("china.openbmb.minicpm")
        self.assertEqual(p.origin, "china")
        self.assertIn("on-device", p.capabilities)

    def test_filtering(self):
        china = list_providers(origin="china")
        self.assertTrue(china)
        self.assertTrue(all(p.origin == "china" for p in china))

    def test_policy_gate(self):
        p = assert_allowed_for_runtime(
            "china.qwen.qwen3",
            approved_origins={"china"},
            capability="llm",
        )
        self.assertEqual(p.project, "Qwen3")

    def test_policy_gate_rejects_capability_mismatch(self):
        with self.assertRaisesRegex(RuntimeError, "CAPABILITY_MISMATCH"):
            assert_allowed_for_runtime(
                "india.ai4bharat.indictrans2",
                approved_origins={"india"},
                capability="tts",
            )


if __name__ == "__main__":
    unittest.main()
